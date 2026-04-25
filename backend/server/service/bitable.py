"""值班表 / 问题原因表：从飞书多维表格同步到 PG，并提供查询；
工单批量上传到飞书多维表格"""
import json
import logging
import re
from datetime import date

import httpx
from sqlalchemy import BigInteger
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import col, select

from server.exception.biz_error import BizError
from server.model.bot_reply import BotReply
from server.model.duty_schedule import DutySchedule
from server.model.message import Message
from server.model.qa_tracking import QaTracking
from server.utils.date_helper import get_date_range_epoch_ms
from server.utils.db_helper import AsyncSession
from server.utils.lark_bitable_helper import (
    get_tenant_access_token,
    list_bitable_records,
)

logger = logging.getLogger(__name__)

DUTY_BITABLE_APP_TOKEN = "MkoQwxWq7i0fW9kEJk6cjDaKnCe"
DUTY_TABLE_ID = "tblwel6L7Yk9NUpU"

QA_TRACKING_APP_TOKEN = "QNstwKyaNihYv2kKcY4c2RZdn6d"
QA_TRACKING_TABLE_ID = "tblMSns5snZtf14F"

UPLOAD_DEFAULT_APP_TOKEN = "Sywxb4dh8aeRZJsvD3WcDiXDnnc"
UPLOAD_DEFAULT_TABLE_ID = "tblt7L2vgw70yE3F"

_FEEDBACK_ID_RE = re.compile(r"【反馈ID】[：:]\s*(\S+)")


# ─── 值班表 ──────────────────────────────────────────────


def _extract_duty_user_name(row: dict) -> str:
    for key in ("测试", "值班人", "值班人员", "负责人", "处理人"):
        value = (row or {}).get(key)
        if value:
            return str(value).strip()
    return ""


def _parse_duty_date(raw: str) -> date | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    if re.fullmatch(r"\d{13}", raw):
        try:
            return date.fromtimestamp(int(raw) / 1000)
        except Exception:
            return None
    try:
        return date.fromisoformat(raw[:10])
    except Exception:
        return None


async def get_duty_records(session: AsyncSession) -> dict:
    """从 PG 读取值班表，按日期倒序"""
    statement = select(DutySchedule).order_by(col(DutySchedule.duty_date).desc())
    result = await session.exec(statement)
    rows = list(result.all())
    records = [{"日期": r.duty_date.isoformat(), "值班人": r.duty_user} for r in rows]
    return {
        "total": len(records),
        "field_keys": ["日期", "值班人"],
        "records": records,
    }


async def sync_duty_to_pg(session: AsyncSession) -> int:
    """从飞书值班多维表格拉取数据，UPSERT 到 duty_schedule 表"""
    data = await list_bitable_records(DUTY_BITABLE_APP_TOKEN, DUTY_TABLE_ID)
    records: list[dict] = []
    for row in data.get("records", []):
        duty_date = _parse_duty_date(str(row.get("日期") or ""))
        duty_user = _extract_duty_user_name(row)
        if duty_date and duty_user:
            records.append({"duty_date": duty_date, "duty_user": duty_user})

    if records:
        stmt = pg_insert(DutySchedule).values(records)
        upsert = stmt.on_conflict_do_update(
            index_elements=["duty_date"],
            set_={"duty_user": stmt.excluded.duty_user},
        )
        await session.execute(upsert)
        await session.commit()

    logger.info("值班表已同步 %d 条", len(records))
    return len(records)


# ─── 问题原因表 ─────────────────────────────────────────


async def get_qa_tracking_records(session: AsyncSession) -> dict:
    """从 PG 读取 QA 跟进表"""
    statement = select(QaTracking)
    result = await session.exec(statement)
    rows = list(result.all())
    if not rows:
        return {"total": 0, "field_keys": [], "records": []}

    all_keys: dict[str, None] = {}
    records: list[dict] = []
    for r in rows:
        row = {"feedback_id": r.feedback_id, **(r.raw_data or {})}
        for k in row:
            all_keys.setdefault(k, None)
        records.append(row)
    field_keys = list(all_keys)
    return {"total": len(records), "field_keys": field_keys, "records": records}


async def sync_qa_tracking_to_pg(session: AsyncSession) -> int:
    """从飞书 QA 跟进多维表格拉取数据，UPSERT 到 qa_tracking 表"""
    data = await list_bitable_records(
        QA_TRACKING_APP_TOKEN, QA_TRACKING_TABLE_ID, max_records=5000
    )
    records: list[dict] = []
    for row in data.get("records", []):
        desc = row.get("反馈问题详细描述") or ""
        m = _FEEDBACK_ID_RE.search(desc)
        if m:
            records.append({"feedback_id": m.group(1), "raw_data": row})

    if records:
        stmt = pg_insert(QaTracking).values(records)
        upsert = stmt.on_conflict_do_update(
            index_elements=["feedback_id"],
            set_={"raw_data": stmt.excluded.raw_data},
        )
        await session.execute(upsert)
        await session.commit()

    logger.info("问题原因表已同步 %d 条", len(records))
    return len(records)


# ─── 工单上传 ───────────────────────────────────────────


# 多维表格"状态"字段映射：bot_reply.problem_category 前缀 → 状态
_STATUS_PREFIX_MAP: list[tuple[str, str]] = [
    ("技术问题", "技术"),
    ("非技术问题", "非技术"),
]


def _classify_status(bot_reply: BotReply | None) -> str:
    pc = (bot_reply.problem_category or "") if bot_reply else ""
    for prefix, label in _STATUS_PREFIX_MAP:
        if pc.startswith(prefix):
            return label
    return "待定"


def _extract_elements_text(elements: list) -> str:
    """飞书 post / interactive 卡片 elements 数组提取纯文本"""
    lines: list[str] = []
    for row in elements:
        if not isinstance(row, list):
            continue
        pieces: list[str] = []
        for el in row:
            if not isinstance(el, dict):
                continue
            tag = el.get("tag")
            if tag in ("text", "a"):
                pieces.append(str(el.get("text") or ""))
            elif tag == "at":
                pieces.append(f"@{el.get('user_name') or '用户'}")
        joined = "".join(pieces).strip()
        if joined:
            lines.append(joined)
    return "\n".join(lines)


def _prepend_mention_keys(reply: Message, text: str) -> str:
    """飞书纯文本里 @ 可能只在 raw_data.mentions 数组里出现，正文未带就补上"""
    text = (text or "").strip()
    raw = reply.raw_data if isinstance(reply.raw_data, dict) else {}
    mentions = raw.get("mentions")
    if not isinstance(mentions, list) or not mentions:
        return text
    keys: list[str] = []
    for m in mentions:
        if isinstance(m, dict):
            k = (m.get("key") or "").strip()
            if k and k not in keys:
                keys.append(k)
    if not keys:
        return text
    if not text:
        return "\n".join(keys)
    if any(k in text for k in keys):
        return text
    return "\n".join(keys) + "\n" + text


def _extract_reply_text(reply: Message) -> str:
    """从单条回复 raw_data 中提取纯文本，自动跳过"自动排查单"机器人卡片"""
    raw = reply.raw_data if isinstance(reply.raw_data, dict) else {}
    msg_type = raw.get("msg_type")
    body = raw.get("body") or {}
    content_raw = body.get("content")

    parsed: dict | str | None = None
    if isinstance(content_raw, str):
        s = content_raw.strip()
        if not s:
            return ""
        try:
            parsed = json.loads(s)
        except json.JSONDecodeError:
            parsed = s
    elif isinstance(content_raw, dict):
        parsed = content_raw

    # 纯文本消息
    if msg_type == "text":
        if isinstance(parsed, dict):
            return _prepend_mention_keys(reply, str(parsed.get("text") or ""))
        if isinstance(parsed, str):
            return _prepend_mention_keys(reply, parsed)
        return ""

    # post / interactive 卡片
    if isinstance(parsed, dict):
        title = str(parsed.get("title") or "").strip()
        if title.startswith("自动排查单"):
            return ""
        parts: list[str] = []
        if title:
            parts.append(title)
        elements = parsed.get("elements") or parsed.get("content")
        if isinstance(elements, list):
            t = _extract_elements_text(elements)
            if t:
                parts.append(t)
        return _prepend_mention_keys(reply, "\n".join(parts).strip())

    return ""


def _resolve_record_date_ms(thread: Message) -> int | None:
    """工单"日期"列取值：直接使用 raw_data.create_time（飞书消息的毫秒戳）"""
    raw = thread.raw_data if isinstance(thread.raw_data, dict) else {}
    ct = raw.get("create_time")
    if ct is None:
        return None
    try:
        return int(ct)
    except (TypeError, ValueError):
        return None


def _build_record_fields(
    thread: Message,
    replies: list[Message],
    bot_reply: BotReply | None,
) -> dict:
    """主消息 + 回复 + bot_reply → 多维表格字段。
    "日期"列严格使用每条工单自身的真实反馈日期，不再支持外部 report_date 覆盖。
    """
    parsed = thread.parsed_data if isinstance(thread.parsed_data, dict) else {}
    content = parsed.get("content") if isinstance(parsed, dict) else None
    content = content if isinstance(content, dict) else {}

    feedback_id = str(content.get("feedback_id") or thread.id)
    user_content = str(content.get("user_content") or "")
    client_type = str(content.get("client_type") or "无法判断") or "无法判断"

    reply_texts = [_extract_reply_text(r) for r in replies]
    reply_content = "\n---\n".join(t for t in reply_texts if t)

    fields: dict = {
        "反馈 ID": feedback_id,
        "反馈原文": user_content,
        "回复内容": reply_content,
        "状态": _classify_status(bot_reply),
        "客户端": client_type,
    }

    record_date_ms = _resolve_record_date_ms(thread)
    if record_date_ms is not None:
        fields["日期"] = record_date_ms

    return fields


async def upload_feedbacks(
    session: AsyncSession,
    start_date: str | None,
    end_date: str | None,
    app_token: str,
    table_id: str,
) -> dict:
    """将指定日期范围内的工单批量上传到飞书多维表格。
    多维表格中"日期"列使用每条工单自身的真实反馈日期。
    """
    token = await get_tenant_access_token()
    if not token:
        raise BizError("无法获取飞书访问令牌，请检查 LARK_APP_ID / LARK_APP_SECRET 配置")

    base_where = col(Message.type) == "thread"
    start_ms, end_ms = get_date_range_epoch_ms(start_date, end_date)
    if start_ms is not None or end_ms is not None:
        ct_ms = col(Message.raw_data)["create_time"].astext.cast(BigInteger)
        if start_ms is not None:
            base_where = base_where & (ct_ms >= start_ms)
        if end_ms is not None:
            base_where = base_where & (ct_ms <= end_ms)

    threads_result = await session.exec(
        select(Message).where(base_where).order_by(col(Message.id))
    )
    threads = list(threads_result.all())

    if not threads:
        return {"total": 0, "uploaded": 0, "failed": 0, "errors": []}

    main_ids = [t.id for t in threads]

    rep_parent = col(Message.raw_data)["parent_id"].astext
    replies_result = await session.exec(
        select(Message)
        .where(rep_parent.in_(main_ids))
        .order_by(rep_parent, col(Message.id))
    )
    reply_map: dict[str, list[Message]] = {}
    for r in replies_result.all():
        pid = (r.raw_data or {}).get("parent_id") if isinstance(r.raw_data, dict) else None
        if isinstance(pid, str):
            reply_map.setdefault(pid, []).append(r)

    bot_reply_result = await session.exec(
        select(BotReply).where(col(BotReply.ticket_id).in_(main_ids))
    )
    bot_reply_map = {br.ticket_id: br for br in bot_reply_result.all()}

    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    total = len(threads)
    uploaded = 0
    failed = 0
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=15) as client:
        for thread in threads:
            replies = reply_map.get(thread.id, [])
            br = bot_reply_map.get(thread.id)
            fields = _build_record_fields(thread, replies, br)
            feedback_id = fields.get("反馈 ID", "unknown")
            try:
                res = await client.post(url, headers=headers, json={"fields": fields})
                data = res.json()
                if data.get("code") == 0:
                    uploaded += 1
                else:
                    failed += 1
                    errors.append(
                        f"反馈ID {feedback_id}: {data.get('msg', 'Unknown error')}"
                    )
            except Exception as e:
                failed += 1
                errors.append(f"反馈ID {feedback_id}: {e}")

    logger.info(
        "工单上传完成 total=%s uploaded=%s failed=%s", total, uploaded, failed
    )
    return {"total": total, "uploaded": uploaded, "failed": failed, "errors": errors}
