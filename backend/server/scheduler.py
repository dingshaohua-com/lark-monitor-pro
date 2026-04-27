"""定时同步调度器

每天 00:01 (UTC+8) 自动执行：
1. 同步近 3 天飞书群原始消息（含话题回复）到 message 表
2. 同步飞书多维表格（值班表 + QA 跟进表）到 PG
"""

import asyncio
import logging
from datetime import date, datetime, time as dtime, timedelta, timezone

from server.utils.db_helper import annotation_db, lark_monitor_db

logger = logging.getLogger(__name__)

_task: asyncio.Task | None = None

# 每天执行时刻（UTC+8）
_RUN_AT = dtime(0, 1)
# 同步近 N 天
_RECENT_DAYS = 3


async def _wait_until(target: dtime) -> None:
    """睡眠到当天或次日的 target 时刻（UTC+8）"""
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    next_run = datetime.combine(now.date(), target, tzinfo=tz)
    if next_run <= now:
        next_run += timedelta(days=1)
    delta = (next_run - now).total_seconds()
    logger.info("⏰ 定时同步: 下次执行时间 %s (%.0f 秒后)", next_run.isoformat(), delta)
    await asyncio.sleep(delta)


async def _sync_recent_messages() -> None:
    """同步近 N 天的飞书群消息到 message 表"""
    from server.service.message import sync as sync_messages

    today = date.today()
    start = today - timedelta(days=_RECENT_DAYS - 1)
    end = today
    logger.info("📥 消息同步: 开始 %s ~ %s", start, end)
    try:
        async with lark_monitor_db.session_maker() as session:
            try:
                await sync_messages(session, start, end)
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        logger.info("✅ 消息同步: 完成")
    except Exception:
        logger.exception("❌ 消息同步: 执行失败")


async def _sync_bot_reply() -> None:
    """从 annotation_db 全量同步 bot_reply 到本地"""
    from server.service.bot_reply import sync_bot_reply

    logger.info("📥 bot_reply 同步: 开始")
    try:
        async with annotation_db.session_maker() as src_session, \
                lark_monitor_db.session_maker() as dst_session:
            try:
                count = await sync_bot_reply(src_session, dst_session)
                await dst_session.commit()
            except Exception:
                await dst_session.rollback()
                raise
        logger.info("✅ bot_reply 同步: 完成 (%d 条)", count)
    except Exception:
        logger.exception("❌ bot_reply 同步: 执行失败")


async def _sync_bitable() -> None:
    """同步飞书多维表格（值班表 + QA 跟进表）到 PG"""
    from server.service.bitable import sync_duty_to_pg, sync_qa_tracking_to_pg

    logger.info("📥 多维表格同步: 开始")
    try:
        async with lark_monitor_db.session_maker() as session:
            try:
                duty_count = await sync_duty_to_pg(session)
                qa_count = await sync_qa_tracking_to_pg(session)
                await session.commit()
            except Exception:
                await session.rollback()
                raise
        logger.info(
            "✅ 多维表格同步: 完成 (值班表 %d 条, QA 跟进表 %d 条)", duty_count, qa_count
        )
    except Exception:
        logger.exception("❌ 多维表格同步: 执行失败")


async def run_once() -> None:
    """立即执行一次同步（手动触发用）"""
    await _sync_recent_messages()
    await _sync_bot_reply()
    await _sync_bitable()


async def _scheduler_loop() -> None:
    while True:
        try:
            await _wait_until(_RUN_AT)
            await _sync_recent_messages()
            await _sync_bot_reply()
            await _sync_bitable()
        except asyncio.CancelledError:
            raise
        except Exception:
            # 兜底：调度器本身出错时，避免循环退出，等 60s 后重试
            logger.exception("调度器循环异常，60s 后重试")
            await asyncio.sleep(60)


def start_scheduler() -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_scheduler_loop())
        logger.info("🚀 定时同步调度器已启动 (每日 %s UTC+8)", _RUN_AT.strftime("%H:%M"))


def stop_scheduler() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        logger.info("🛑 定时同步调度器已停止")
    _task = None
