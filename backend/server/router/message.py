from datetime import date
from fastapi import APIRouter
import server.service.message as work_order_service
from fastapi import Depends
from server.utils.db_helper import lark_monitor_db, AsyncSession


router = APIRouter(prefix="/message", tags=["work-order"])

@router.get("")
async def get_all( session: AsyncSession = Depends(lark_monitor_db.get_session),start: date | None = None, end: date | None = None):
    result = await work_order_service.get_one(session)
    return result

