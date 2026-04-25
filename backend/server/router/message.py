from typing import List
import server.service.message as message_service
from server.model.message import Message
from server.schema.common import Page, SyncRequest
from server.schema.message import MessageWithReplies
from server.utils.db_helper import lark_monitor_db, AsyncSession
from fastapi import APIRouter, Body, Depends, Query



router = APIRouter(prefix="/message", tags=["work-order"])

@router.get("")
async def query(
    session: AsyncSession = Depends(lark_monitor_db.get_session),
    id: str | None = None,
    withReply: bool = Query(default=False, description="为 true 时同时返回主消息下 raw_data.parent_id 指向主消息 id 的回复"),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始（仅列表查询有效）"),
    pageSize: int | None = Query(default=None, ge=1, le=10000, description="每页条数。不传则不分页，返回全部（导出场景用）"),
    keyword: str | None = Query(default=None, description="按用户原文模糊搜索（仅列表查询有效）"),
    problemCategory: str | None = Query(default=None, description="按机器人问题分类过滤（仅列表查询有效）"),
    startDate: str | None = Query(default=None, description="反馈起始日期 YYYY-MM-DD（含）"),
    endDate: str | None = Query(default=None, description="反馈结束日期 YYYY-MM-DD（含）"),
    hasBotProcessed: str | None = Query(default=None, description="机器人是否处理过：yes / no"),
    dutyUser: str | None = Query(default=None, description="按值班人模糊匹配（关联 duty_schedule 表）"),
    hasQaTracking: str | None = Query(default=None, description="问题原因是否已跟进：yes / no"),
) -> MessageWithReplies | Message | Page[MessageWithReplies] | Page[Message] | None:
    if id is not None:
        return await message_service.get_one(session, id, with_reply=withReply)
    return await message_service.get_list(
        session,
        with_reply=withReply,
        page=page,
        page_size=pageSize,
        keyword=keyword,
        problem_category=problemCategory,
        start_date=startDate,
        end_date=endDate,
        has_bot_processed=hasBotProcessed,
        duty_user=dutyUser,
        has_qa_tracking=hasQaTracking,
    )


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


@router.get("/stats")
async def stats(
    session: AsyncSession = Depends(lark_monitor_db.get_session),
    start_date: str | None = Query(default=None, description="起始日期 YYYY-MM-DD（默认近 7 天）"),
    end_date: str | None = Query(default=None, description="结束日期 YYYY-MM-DD（默认今天）"),
):
    """数据分析：当前周期 vs 前一周期的工单/机器人统计 + 问题分类分布"""
    return await message_service.get_stats(session, start_date=start_date, end_date=end_date)