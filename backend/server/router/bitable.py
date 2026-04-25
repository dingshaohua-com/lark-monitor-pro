from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel, Field

import server.service.bitable as bitable_service
from server.utils.db_helper import AsyncSession, lark_monitor_db

router = APIRouter(prefix="/bitable", tags=["bitable"])


class UploadRequest(BaseModel):
    """上传工单到飞书多维表格的请求体"""

    start_date: str | None = Field(None, description="起始日期 YYYY-MM-DD")
    end_date: str | None = Field(None, description="结束日期 YYYY-MM-DD")
    app_token: str = Field(
        bitable_service.UPLOAD_DEFAULT_APP_TOKEN, description="多维表格 App Token"
    )
    table_id: str = Field(
        bitable_service.UPLOAD_DEFAULT_TABLE_ID, description="多维表格 Table ID"
    )


class UploadResponse(BaseModel):
    """上传结果"""

    total: int
    uploaded: int
    failed: int
    errors: list[str]


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


@router.post("/upload")
async def upload(
    body: UploadRequest = Body(...),
    session: AsyncSession = Depends(lark_monitor_db.get_session),
) -> UploadResponse:
    """将指定日期范围内的工单批量上传到飞书多维表格"""
    result = await bitable_service.upload_feedbacks(
        session,
        start_date=body.start_date,
        end_date=body.end_date,
        app_token=body.app_token,
        table_id=body.table_id,
    )
    return UploadResponse(**result)
