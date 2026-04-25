from fastapi import APIRouter, Depends

import server.service.bitable as bitable_service
from server.utils.db_helper import AsyncSession, lark_monitor_db

router = APIRouter(prefix="/bitable", tags=["bitable"])


@router.get("/duty-records")
async def duty_records(
    session: AsyncSession = Depends(lark_monitor_db.get_session),
):
    """从 PG 读取值班表数据"""
    return await bitable_service.get_duty_records(session)


@router.get("/qa-tracking-records")
async def qa_tracking_records(
    session: AsyncSession = Depends(lark_monitor_db.get_session),
):
    """从 PG 读取 QA 跟进（问题原因）表数据"""
    return await bitable_service.get_qa_tracking_records(session)


@router.post("/sync-duty")
async def sync_duty(
    session: AsyncSession = Depends(lark_monitor_db.get_session),
):
    """手动同步值班表（飞书多维表格 → PG）"""
    count = await bitable_service.sync_duty_to_pg(session)
    return {"synced": count}


@router.post("/sync-qa-tracking")
async def sync_qa_tracking(
    session: AsyncSession = Depends(lark_monitor_db.get_session),
):
    """手动同步 QA 跟进（问题原因）表（飞书多维表格 → PG）"""
    count = await bitable_service.sync_qa_tracking_to_pg(session)
    return {"synced": count}
