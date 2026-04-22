from functools import partial
from datetime import date, datetime
from server.utils.lark_oapi_helper import get_msgs
from fastapi import Depends
from server.model.message import Message
from server.utils.db_helper import lark_monitor_db, AsyncSession


async def get_all():
    return []


async def get_one(session: AsyncSession):
    #
    # session: AsyncSession = lark_monitor_db.get_session();
    msg = await session.get(Message, 2)
    return msg



# async def sync(start: date | None = None, end: date | None = None) :
#     """从飞书群拉取原始消息（含话题回复）同步到表"""
#     raw_col = get_collection("raw_msg")
#     bound_callback = partial(sync_collection, raw_col)
#     await get_msgs(start, end, bound_callback)
#     return True