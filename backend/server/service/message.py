from datetime import date
from typing import List
from functools import partial
from sqlalchemy import case, or_
from sqlmodel import select, col
from server.model.message import Message
from server.model.bot_reply import BotReply
from server.utils.sync_table_helper import sync_table_helper
from server.utils.db_helper import lark_monitor_db, AsyncSession
from server.utils.lark_oapi_helper import get_msgs


async def get_all():
    return []

async def get_one(session: AsyncSession, id: str) -> Message:
    msg = await session.get(Message, id)
    return msg

async def get_list(session: AsyncSession, with_reply: bool = False) -> List[Message]:
    """默认只查主消息 (type=thread)。with_reply=True 时额外带上 raw_data.parent_id 指向这些主消息的回复。"""
    if with_reply:
        main_ids_subq = select(col(Message.id)).where(col(Message.type) == "thread")
        rep_parent = col(Message.raw_data)["parent_id"].astext
        statement = (
            select(Message)
            .where(
                or_(
                    col(Message.type) == "thread",
                    rep_parent.in_(main_ids_subq),
                )
            )
            .order_by(
                case((col(Message.type) == "thread", 0), else_=1),
                rep_parent.nullsfirst(),
                col(Message.id),
            )
        )
    else:
        statement = select(Message).where(col(Message.type) == "thread")
    result = await session.exec(statement)
    messages = list(result.all())

    # bot_reply 表随机器人回复变化，在列表时按需关联，避免每次同步时写入过期快照
    thread_ids = [m.id for m in messages if m.type == "thread"]
    if not thread_ids:
        return messages

    stmt = select(BotReply).where(BotReply.ticket_id.in_(thread_ids))
    br_result = await session.exec(stmt)
    bot_reply_map = {br.ticket_id: br for br in br_result.all()}

    for m in messages:
        if m.type != "thread":
            continue
        br = bot_reply_map.get(m.id)
        pd = dict(m.parsed_data) if m.parsed_data else {}
        pd["bot_analysis"] = br.model_dump(mode="json") if br else None
        m.parsed_data = pd

    return messages



async def sync(session: AsyncSession, start: date | None = None, end: date | None = None) :
    """从飞书群拉取原始消息（含话题回复）同步到表"""
    bound_callback = partial(sync_table_helper, session)
    await get_msgs(start, end, bound_callback)
    return True