from typing import Annotated
import server.service.message as message_service
from server.model.message import Message
from server.schema.common import Page, SyncRequest
from server.schema.message import MessageListQuery, MessageWithReplies
from server.utils.db_helper import lark_monitor_db, AsyncSession
from fastapi import APIRouter, Body, Depends, Query


router = APIRouter(prefix="/message", tags=["work-order"])


@router.get("")
async def list_messages(
    session: AsyncSession = Depends(lark_monitor_db.get_session),
    query: Annotated[MessageListQuery, Query()] = MessageListQuery(),
) -> Page[MessageWithReplies] | Page[Message]:
    """主消息列表查询，支持多条件筛选 + 分页 / 不分页（导出）。"""
    return await message_service.get_list(
        session, filter=query, with_reply=query.with_reply
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


# 路径参数路由放最后，避免吃掉上面的 /sync /stats
@router.get("/{message_id}")
async def get_message(
    message_id: str,
    session: AsyncSession = Depends(lark_monitor_db.get_session),
    with_reply: bool = Query(
        default=False,
        alias="withReply",
        description="为 true 时同时返回主消息下 raw_data.parent_id 指向主消息 id 的回复",
    ),
) -> MessageWithReplies | Message | None:
    """按 id 查询单条工单，找不到返回 null（与项目统一响应包装兼容）。"""
    return await message_service.get_one(session, message_id, with_reply=with_reply)
