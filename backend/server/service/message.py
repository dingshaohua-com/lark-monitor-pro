from datetime import date
from typing import List
from functools import partial
from sqlmodel import select, col
from server.model.message import Message
from server.utils.sync_table_helper import sync_table_helper
from server.utils.db_helper import lark_monitor_db, AsyncSession
from server.utils.lark_oapi_helper import get_msgs


async def get_all():
    return []

async def get_one(session: AsyncSession, id: str) -> Message:
    msg = await session.get(Message, id)
    return msg

async def get_all(session: AsyncSession)->List[Message]:
    statement = select(Message) # 1. 像写 SQL 一样构建语句：SELECT * FROM message
    result = await session.exec(statement)  # 2. 执行并等待结果 (注意：session.exec 是异步的)
    messages = result.all()  # 3. 拿到所有对象的列表
    return messages



async def sync(session: AsyncSession, start: date | None = None, end: date | None = None) :
    """从飞书群拉取原始消息（含话题回复）同步到表"""
    bound_callback = partial(sync_table_helper, session)
    await get_msgs(start, end, bound_callback)
    return True