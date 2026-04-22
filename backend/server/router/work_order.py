from datetime import date
from fastapi import APIRouter
import server.service.work_order as work_order_service

router = APIRouter(prefix="/work-order", tags=["work-order"])

@router.get("")
async def get_all(start: date | None = None, end: date | None = None):
    result = await work_order_service.get_all()
    return result

