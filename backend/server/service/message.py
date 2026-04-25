from datetime import date, timedelta
from typing import List
from functools import partial
from sqlalchemy import BigInteger, func
from sqlmodel import select, col
from server.model.message import Message
from server.model.bot_reply import BotReply
from server.model.duty_schedule import DutySchedule
from server.model.qa_tracking import QaTracking
from server.schema.common import Page
from server.schema.message import MessageWithReplies
from server.utils.sync_table_helper import sync_table_helper
from server.utils.db_helper import lark_monitor_db, AsyncSession
from server.utils.lark_oapi_helper import get_msgs
from server.utils.date_helper import get_date_range_epoch_ms


async def _query_replies(session: AsyncSession, main_ids: List[str]) -> List[Message]:
    """查询 raw_data.parent_id 指向给定主消息 id 的回复消息"""
    if not main_ids:
        return []
    rep_parent = col(Message.raw_data)["parent_id"].astext
    statement = (
        select(Message)
        .where(rep_parent.in_(main_ids))
        .order_by(rep_parent, col(Message.id))
    )
    result = await session.exec(statement)
    return list(result.all())


async def _attach_bot_processed(session: AsyncSession, messages: List[Message]) -> None:
    """给主消息(type=thread)的 parsed_data 附加 bot_processed 字段。

    bot_reply 表随机器人回复变化，查询时按需关联，避免同步时写入过期快照。
    """
    thread_ids = [m.id for m in messages if m.type == "thread"]
    if not thread_ids:
        return

    stmt = select(BotReply).where(BotReply.ticket_id.in_(thread_ids))
    br_result = await session.exec(stmt)
    bot_reply_map = {br.ticket_id: br for br in br_result.all()}

    for m in messages:
        if m.type != "thread":
            continue
        br = bot_reply_map.get(m.id)
        pd = dict(m.parsed_data) if m.parsed_data else {}
        pd["bot_processed"] = br.model_dump(mode="json") if br else None
        m.parsed_data = pd


def _resolve_duty_date(msg: Message) -> date | None:
    """从主消息推导值班日期：优先 parsed_data.content.feedback_time(YYYY-MM-DD...)，否则 raw_data.create_time(毫秒戳)"""
    parsed = msg.parsed_data or {}
    content = parsed.get("content") if isinstance(parsed, dict) else None
    if isinstance(content, dict):
        ft = content.get("feedback_time")
        if isinstance(ft, str) and len(ft) >= 10:
            try:
                return date.fromisoformat(ft[:10])
            except Exception:
                pass

    raw = msg.raw_data or {}
    ct = raw.get("create_time") if isinstance(raw, dict) else None
    if ct:
        try:
            return date.fromtimestamp(int(ct) / 1000)
        except Exception:
            pass
    return None


async def _attach_duty_and_qa(session: AsyncSession, messages: List[Message]) -> None:
    """给主消息(type=thread)的 parsed_data 附加 duty_user 与 qa_tracking。

    - duty_user：按反馈日期在 duty_schedule 表查到的值班人，未匹配时为空串
    - qa_tracking：按 feedback_id 在 qa_tracking 表查到的整行字段(dict)，未匹配时为 None
    """
    threads = [m for m in messages if m.type == "thread"]
    if not threads:
        return

    msg_to_duty_date: dict[str, date] = {}
    msg_to_feedback_id: dict[str, str] = {}
    for m in threads:
        d = _resolve_duty_date(m)
        if d:
            msg_to_duty_date[m.id] = d
        content = (m.parsed_data or {}).get("content") if isinstance(m.parsed_data, dict) else None
        if isinstance(content, dict):
            fid = content.get("feedback_id")
            if isinstance(fid, str) and fid.strip():
                msg_to_feedback_id[m.id] = fid.strip()

    duty_map: dict[date, str] = {}
    duty_dates = list(set(msg_to_duty_date.values()))
    if duty_dates:
        stmt = select(DutySchedule).where(col(DutySchedule.duty_date).in_(duty_dates))
        result = await session.exec(stmt)
        for r in result.all():
            duty_map[r.duty_date] = r.duty_user

    qa_map: dict[str, dict] = {}
    feedback_ids = list(set(msg_to_feedback_id.values()))
    if feedback_ids:
        stmt = select(QaTracking).where(col(QaTracking.feedback_id).in_(feedback_ids))
        result = await session.exec(stmt)
        for r in result.all():
            qa_map[r.feedback_id] = dict(r.raw_data or {})

    for m in threads:
        pd = dict(m.parsed_data) if m.parsed_data else {}
        d = msg_to_duty_date.get(m.id)
        pd["duty_user"] = duty_map.get(d, "") if d else ""
        fid = msg_to_feedback_id.get(m.id)
        pd["qa_tracking"] = qa_map.get(fid) if fid else None
        m.parsed_data = pd


def _nest_replies(
    threads: List[Message], replies: List[Message]
) -> List[MessageWithReplies]:
    """把扁平的 [thread...] + [reply...] 转成嵌套 MessageWithReplies 列表"""
    by_parent: dict[str, list[Message]] = {}
    for r in replies:
        pid = (r.raw_data or {}).get("parent_id") if isinstance(r.raw_data, dict) else None
        if isinstance(pid, str):
            by_parent.setdefault(pid, []).append(r)

    return [
        MessageWithReplies(
            id=t.id,
            type=t.type,
            parsed_data=t.parsed_data or {},
            raw_data=t.raw_data or {},
            replies=by_parent.get(t.id, []),
        )
        for t in threads
    ]


async def get_one(
    session: AsyncSession, id: str, with_reply: bool = False
) -> Message | MessageWithReplies | None:
    """单条工单查询。with_reply=True 时返回 MessageWithReplies（含 replies 字段）；否则返回 Message。"""
    msg = await session.get(Message, id)
    if msg is None:
        return None

    if with_reply and msg.type == "thread":
        replies = await _query_replies(session, [msg.id])
        await _attach_bot_processed(session, [msg, *replies])
        await _attach_duty_and_qa(session, [msg])
        return _nest_replies([msg], replies)[0]

    await _attach_bot_processed(session, [msg])
    await _attach_duty_and_qa(session, [msg])
    return msg


async def get_list(
    session: AsyncSession,
    with_reply: bool = False,
    page: int = 1,
    page_size: int | None = 20,
    keyword: str | None = None,
    problem_category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    has_bot_processed: str | None = None,
    duty_user: str | None = None,
    has_qa_tracking: str | None = None,
) -> Page[Message] | Page[MessageWithReplies]:
    """默认只查主消息 (type=thread)。with_reply=True 时每条 item 多一个 replies 字段（嵌套结构）。
    page_size=None 时不分页，返回全部（导出场景）。

    过滤项（全部 SQL 层完成）：
    - keyword            → parsed_data.content.user_content ILIKE
    - problem_category   → 关联 bot_reply 表过滤
    - start_date / end_date → raw_data.create_time(毫秒戳) 做范围过滤
    - has_bot_processed  → "yes"/"no"，工单是否在 bot_reply 表里有记录
    - duty_user          → 先查 duty_schedule 拿匹配日期，再用 feedback_time 前 10 位 IN
    - has_qa_tracking    → "yes"/"no"，工单 feedback_id 是否在 qa_tracking 表里
    """
    base_where = col(Message.type) == "thread"
    if keyword and keyword.strip():
        user_content = col(Message.parsed_data)["content"]["user_content"].astext
        base_where = base_where & user_content.ilike(f"%{keyword.strip()}%")
    if problem_category:
        ticket_subq = select(col(BotReply.ticket_id)).where(
            col(BotReply.problem_category) == problem_category
        )
        base_where = base_where & col(Message.id).in_(ticket_subq)

    start_ms, end_ms = get_date_range_epoch_ms(start_date, end_date)
    if start_ms is not None or end_ms is not None:
        create_time_ms = col(Message.raw_data)["create_time"].astext.cast(BigInteger)
        if start_ms is not None:
            base_where = base_where & (create_time_ms >= start_ms)
        if end_ms is not None:
            base_where = base_where & (create_time_ms <= end_ms)

    if has_bot_processed in ("yes", "no"):
        bot_exists = (
            select(BotReply.ticket_id)
            .where(col(BotReply.ticket_id) == col(Message.id))
            .exists()
        )
        base_where = base_where & (bot_exists if has_bot_processed == "yes" else ~bot_exists)

    duty_user_kw = (duty_user or "").strip()
    if duty_user_kw:
        # 先查 duty_schedule 拿到该值班人对应的所有日期
        dates_stmt = select(col(DutySchedule.duty_date)).where(
            col(DutySchedule.duty_user).ilike(f"%{duty_user_kw}%")
        )
        dates_result = await session.exec(dates_stmt)
        matched_dates = [d.isoformat() for d in dates_result.all()]
        if not matched_dates:
            return Page[Message](items=[], total=0, page=page, pageSize=page_size or 0)
        # 再用 feedback_time 前 10 位 IN 这些日期字符串
        feedback_date_str = func.substring(
            col(Message.parsed_data)["content"]["feedback_time"].astext, 1, 10
        )
        base_where = base_where & feedback_date_str.in_(matched_dates)

    if has_qa_tracking in ("yes", "no"):
        feedback_id_str = col(Message.parsed_data)["content"]["feedback_id"].astext
        qa_subq = select(col(QaTracking.feedback_id))
        base_where = base_where & (
            feedback_id_str.in_(qa_subq) if has_qa_tracking == "yes" else feedback_id_str.notin_(qa_subq)
        )

    count_stmt = select(func.count()).select_from(Message).where(base_where)
    total = (await session.exec(count_stmt)).one() or 0

    statement = select(Message).where(base_where).order_by(col(Message.id))
    if page_size is not None:
        statement = statement.offset((page - 1) * page_size).limit(page_size)
    result_threads = await session.exec(statement)
    threads = list(result_threads.all())

    await _attach_bot_processed(session, threads)
    await _attach_duty_and_qa(session, threads)

    # 不分页时 pageSize 反映实际拿到的条数
    actual_page_size = page_size if page_size is not None else len(threads)

    if with_reply:
        replies = await _query_replies(session, [m.id for m in threads])
        await _attach_bot_processed(session, replies)
        items = _nest_replies(threads, replies)
        return Page[MessageWithReplies](
            items=items, total=total, page=page, pageSize=actual_page_size
        )

    return Page[Message](items=threads, total=total, page=page, pageSize=actual_page_size)


async def sync(session: AsyncSession, start: date | None = None, end: date | None = None) :
    """从飞书群拉取原始消息（含话题回复）同步到表"""
    bound_callback = partial(sync_table_helper, session)
    await get_msgs(start, end, bound_callback)
    return True


# ── 统计 ─────────────────────────────────────────────────


_CORRECT_CATEGORIES = {"非技术问题-元芳排查正确", "技术问题-转bug，元芳排查正确"}
_INCORRECT_CATEGORIES = {"非技术问题-元芳排查有误", "技术问题-转bug，元芳排查有误"}


async def _calc_period_stats(
    session: AsyncSession, start_date: str, end_date: str
) -> dict:
    """计算单个周期内的统计数据：主消息 + 机器人参与/处理 + 问题分类分布"""
    # 主消息时间范围（基于 raw_data.create_time 毫秒戳）
    base_where = col(Message.type) == "thread"
    start_ms, end_ms = get_date_range_epoch_ms(start_date, end_date)
    if start_ms is not None or end_ms is not None:
        ct_ms = col(Message.raw_data)["create_time"].astext.cast(BigInteger)
        if start_ms is not None:
            base_where = base_where & (ct_ms >= start_ms)
        if end_ms is not None:
            base_where = base_where & (ct_ms <= end_ms)

    # 1. total: 当前周期内的工单（主消息）总数
    total = (
        await session.exec(select(func.count()).select_from(Message).where(base_where))
    ).one() or 0

    # 2. bot_processed: 工单 id 在 bot_reply 表里有记录
    bot_replies_subq = select(col(BotReply.ticket_id))
    bot_processed = (
        await session.exec(
            select(func.count())
            .select_from(Message)
            .where(base_where & col(Message.id).in_(bot_replies_subq))
        )
    ).one() or 0

    # 3. 问题分类分布
    #    先在 bot_reply 上 GROUP BY problem_category 拿到已分类数
    #    再用 total - 已分类总数 得到"待人工确认"（未机器人处理 + 处理但分类为空）
    period_thread_ids_subq = select(col(Message.id)).where(base_where)
    pc_stmt = (
        select(col(BotReply.problem_category), func.count())
        .where(col(BotReply.ticket_id).in_(period_thread_ids_subq))
        .group_by(col(BotReply.problem_category))
    )
    pc_result = await session.exec(pc_stmt)

    problem_category_counts: dict[str, int] = {}
    classified_total = 0
    for pc, cnt in pc_result.all():
        key = pc or "待人工确认"
        problem_category_counts[key] = problem_category_counts.get(key, 0) + cnt
        classified_total += cnt

    unclassified = total - classified_total
    if unclassified > 0:
        problem_category_counts["待人工确认"] = (
            problem_category_counts.get("待人工确认", 0) + unclassified
        )

    correct_count = sum(
        problem_category_counts.get(c, 0) for c in _CORRECT_CATEGORIES
    )
    incorrect_count = sum(
        problem_category_counts.get(c, 0) for c in _INCORRECT_CATEGORIES
    )

    return {
        "total": total,
        "bot_processed": bot_processed,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "problem_category_counts": problem_category_counts,
    }


async def get_stats(
    session: AsyncSession,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """统计分析：当前周期 vs 前一周期"""
    today = date.today()
    if not start_date:
        start_date = (today - timedelta(days=6)).isoformat()
    if not end_date:
        end_date = today.isoformat()

    start_dt = date.fromisoformat(start_date)
    end_dt = date.fromisoformat(end_date)
    period_days = (end_dt - start_dt).days + 1

    prev_end_dt = start_dt - timedelta(days=1)
    prev_start_dt = prev_end_dt - timedelta(days=period_days - 1)

    current = await _calc_period_stats(session, start_date, end_date)
    previous = await _calc_period_stats(
        session, prev_start_dt.isoformat(), prev_end_dt.isoformat()
    )

    return {
        "current": current,
        "previous": previous,
        "period_days": period_days,
    }
