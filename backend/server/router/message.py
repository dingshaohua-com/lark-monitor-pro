from typing import List
import server.service.message as message_service
from server.model.message import Message
from server.schema.common import Page, SyncRequest
from server.utils.db_helper import lark_monitor_db, AsyncSession
from fastapi import APIRouter, Body, Depends, Query



router = APIRouter(prefix="/message", tags=["work-order"])

@router.get("")
async def query(
    session: AsyncSession = Depends(lark_monitor_db.get_session),
    id: str | None = None,
    withReply: bool = Query(default=False, description="为 true 时同时返回主消息下 raw_data.parent_id 指向主消息 id 的回复"),
    page: int = Query(default=1, ge=1, description="页码，从 1 开始（仅列表查询有效）"),
    pageSize: int = Query(default=20, ge=1, le=200, description="每页条数（仅列表查询有效）"),
    keyword: str | None = Query(default=None, description="按用户原文模糊搜索（仅列表查询有效）"),
    problemCategory: str | None = Query(default=None, description="按机器人问题分类过滤（仅列表查询有效）"),
    startDate: str | None = Query(default=None, description="反馈起始日期 YYYY-MM-DD（含）"),
    endDate: str | None = Query(default=None, description="反馈结束日期 YYYY-MM-DD（含）"),
    hasBotProcessed: str | None = Query(default=None, description="机器人是否处理过：yes / no"),
) -> Message | list[Message] | Page[Message]:
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