"""bot_reply 同步：从 annotation_db."BotReply" 全量拉到本地 lark_monitor_pro."BotReply"。

- 源库（annotation_db）只读，目标库（lark_monitor_pro）UPSERT。
- 两边表名 / 字段名完全一致（PascalCase + camelCase 列名），共用 BotReply model。
- 数据量级较小（与工单一对一），全量同步即可。
- 不做删除：源端删除的记录暂留本地，避免源端误删导致历史统计抖动。
  后续如有需要再扩展为按 timestamp 增量 + 显式 tombstone。
"""
import logging
from typing import Iterable

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import select

from server.model.bot_reply import BotReply
from server.utils.db_helper import AsyncSession

logger = logging.getLogger(__name__)

# 单批 UPSERT 条数，避免参数过多触发 PG 限制
_BATCH_SIZE = 500


def _to_row(br: BotReply) -> dict:
    """ORM 对象 → 适配 pg_insert 的纯字段 dict（按数据库列名）"""
    return {
        "id": br.id,
        "ticketId": br.ticket_id,
        "content": br.content,
        "timestamp": br.timestamp,
        "hidden": br.hidden,
        "upvotedBy": list(br.upvoted_by or []),
        "downvotedBy": list(br.downvoted_by or []),
        "problemCategory": br.problem_category,
    }


def _chunked(rows: list[dict], size: int) -> Iterable[list[dict]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


async def sync_bot_reply(
    src_session: AsyncSession, dst_session: AsyncSession
) -> int:
    """从源库全量读取 BotReply，UPSERT 到目标库。返回同步条数。"""
    src_result = await src_session.exec(select(BotReply))
    src_rows = [_to_row(br) for br in src_result.all()]

    if not src_rows:
        logger.info("bot_reply 同步: 源库无数据")
        return 0

    update_cols = {
        "ticketId": None,
        "content": None,
        "timestamp": None,
        "hidden": None,
        "upvotedBy": None,
        "downvotedBy": None,
        "problemCategory": None,
    }

    total = 0
    for batch in _chunked(src_rows, _BATCH_SIZE):
        stmt = pg_insert(BotReply).values(batch)
        upsert = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={k: getattr(stmt.excluded, k) for k in update_cols},
        )
        await dst_session.execute(upsert)
        total += len(batch)

    logger.info("bot_reply 同步: 完成 %d 条", total)
    return total
