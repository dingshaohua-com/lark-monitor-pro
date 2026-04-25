from datetime import date
from typing import List
from functools import partial
from sqlalchemy import BigInteger, func
from sqlmodel import select, col
from server.model.message import Message
from server.model.bot_reply import BotReply
from server.schema.common import Page
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


async def get_one(session: AsyncSession, id: str, with_reply: bool = False) -> Message | List[Message] | None:
    msg = await session.get(Message, id)
    if msg is None:
        return None

    if with_reply and msg.type == "thread":
        replies = await _query_replies(session, [msg.id])
        messages = [msg, *replies]
        await _attach_bot_processed(session, messages)
        return messages

    await _attach_bot_processed(session, [msg])
    return msg


async def get_list(
    session: AsyncSession,
    with_reply: bool = False,
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    problem_category: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    has_bot_processed: str | None = None,
) -> Page[Message]:
    """默认只查主消息 (type=thread)。with_reply=True 时额外带上 raw_data.parent_id 指向这些主消息的回复。

    过滤项（全部 SQL 层完成）：
    - keyword            → parsed_data.content.user_content ILIKE
    - problem_category   → 关联 bot_reply 表过滤
    - start_date / end_date → raw_data.create_time(毫秒戳) 做范围过滤
    - has_bot_processed  → "yes"/"no"，工单是否在 bot_reply 表里有记录
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

    count_stmt = select(func.count()).select_from(Message).where(base_where)
    total = (await session.exec(count_stmt)).one()

    statement = (
        select(Message)
        .where(base_where)
        .order_by(col(Message.id))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.exec(statement)
    messages = list(result.all())

    if with_reply:
        main_ids = [m.id for m in messages]
        replies = await _query_replies(session, main_ids)
        messages.extend(replies)

    await _attach_bot_processed(session, messages)
    return Page[Message](items=messages, total=total or 0, page=page, pageSize=page_size)


async def sync(session: AsyncSession, start: date | None = None, end: date | None = None) :
    """从飞书群拉取原始消息（含话题回复）同步到表"""
    bound_callback = partial(sync_table_helper, session)
    await get_msgs(start, end, bound_callback)
    return True
