from fastapi import APIRouter

import server.service.bot_reply as bot_reply_service
from server.utils.db_helper import annotation_db, lark_monitor_db

router = APIRouter(prefix="/bot-reply", tags=["bot-reply"])


@router.post("/sync")
async def sync_bot_reply():
    """手动同步机器人回复（annotation_db.bot_reply → 本地 lark_monitor_pro.bot_reply）"""
    async with annotation_db.session_maker() as src_session, \
            lark_monitor_db.session_maker() as dst_session:
        try:
            count = await bot_reply_service.sync_bot_reply(src_session, dst_session)
            await dst_session.commit()
        except Exception:
            await dst_session.rollback()
            raise
    return {"synced": count}
