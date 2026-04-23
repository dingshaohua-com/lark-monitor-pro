from typing import List
import server.service.message as message_service
from server.model.message import Message
from server.schema.common import SyncRequest
from server.utils.db_helper import lark_monitor_db, AsyncSession
from fastapi import APIRouter, Body, Depends



router = APIRouter(prefix="/message", tags=["work-order"])

@router.get("")
async def query( session: AsyncSession = Depends(lark_monitor_db.get_session), id: str | None = None)->Message|List[Message]:
    if id is not None:
        return await message_service.get_one(session, id)
    else:
        return await message_service.get_all(session)


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