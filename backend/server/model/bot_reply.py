from datetime import datetime
from typing import List
from sqlalchemy import Column, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, col, select


class BotReply(SQLModel, table=True):
    __tablename__ = "bot_reply"

    id: str = Field(primary_key=True, index=True)
    ticket_id: str = Field(sa_column=Column("ticketId", String, index=True, nullable=False))
    content: str
    timestamp: datetime
    hidden: bool = Field(default=False)
    upvoted_by: List[str] = Field(
        default_factory=list,
        sa_column=Column("upvotedBy", JSONB),
    )
    downvoted_by: List[str] = Field(
        default_factory=list,
        sa_column=Column("downvotedBy", JSONB),
    )
    problem_category: str | None = Field(
        default=None,
        sa_column=Column("problemCategory", String, nullable=True),
    )


# ─── 应用层兜底：bot_reply 当前 ticketId 1对多 ──────────────────────────
# 现状：bot_reply 表理论上应该 ticketId 一对一（一个工单只有一条机器人回复），
#      但线上数据观察到约 18% 的 ticketId 存在重复（疑为占位 + 覆盖时未清旧记录）。
# 兜底：所有读取 bot_reply 的业务查询统一加上 `latest_bot_reply_id_subq()` 过滤,
#      对每个 ticketId 仅保留 timestamp 最大的一条作为"工单的机器人回复"。
# 回滚：后续若上游清理重复 + 加 UNIQUE("ticketId") + UPSERT 写入,
#      可直接删除本函数，所有调用点把对应的 .where(...) 那一行删掉即可。


def latest_bot_reply_id_subq():
    """返回"每个 ticketId 最新一条 bot_reply.id"的子查询。

    用法（与既有查询条件叠加，业务语义不变）：
        stmt = (
            select(BotReply)
            .where(BotReply.id.in_(latest_bot_reply_id_subq()))
            .where(BotReply.ticket_id.in_(thread_ids))
        )
    """
    rn = (
        func.row_number()
        .over(
            partition_by=col(BotReply.ticket_id),
            order_by=col(BotReply.timestamp).desc(),
        )
        .label("rn")
    )
    inner = select(col(BotReply.id).label("id"), rn).subquery()
    return select(inner.c.id).where(inner.c.rn == 1)
