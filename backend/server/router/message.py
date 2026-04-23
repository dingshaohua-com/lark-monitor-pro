from typing import List
import server.service.message as message_service
from server.model.message import Message
from server.schema.common import SyncRequest
from server.utils.db_helper import lark_monitor_db, AsyncSession
from fastapi import APIRouter, Body, Depends, Query



router = APIRouter(prefix="/message", tags=["work-order"])

@router.get("")
async def query(
    session: AsyncSession = Depends(lark_monitor_db.get_session),
    id: str | None = None,
    withReply: bool = Query(default=False, description="为 true 时同时返回主消息下 raw_data.parent_id 指向主消息 id 的回复"),
) -> Message | list[Message]:
    if id is not None:
        return await message_service.get_one(session, id)
    return await message_service.get_list(session, with_reply=withReply)


@router.post("/sync")
async def sync(
    body: SyncRequest = Body(...),
    session: AsyncSession = Depends(lark_monitor_db.get_session),
):
    start = body.start
    end = body.end
    if body.mode == "range" and not start:
        # range 模式必须提供 start
        start = end  # 若只传了 end，用 end 作为 start
    result = await message_service.sync(session, start, end)
    return result