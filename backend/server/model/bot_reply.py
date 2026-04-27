from datetime import datetime
from typing import List
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Field, SQLModel


class BotReply(SQLModel, table=True):
    """机器人回复表（与源库 annotation_db."BotReply" 同名同结构，每日同步过来一份）。

    upvotedBy / downvotedBy 在源库是 Prisma String[]，对应 PG 原生 text[] 数组类型，
    所以这里也要用 ARRAY(String) 匹配，不能用 JSONB。
    """

    __tablename__ = "BotReply"

    id: str = Field(primary_key=True, index=True)
    ticket_id: str = Field(sa_column=Column("ticketId", String, index=True, nullable=False))
    content: str
    timestamp: datetime
    hidden: bool = Field(default=False)
    upvoted_by: List[str] = Field(
        default_factory=list,
        sa_column=Column("upvotedBy", ARRAY(String), nullable=False, server_default="{}"),
    )
    downvoted_by: List[str] = Field(
        default_factory=list,
        sa_column=Column("downvotedBy", ARRAY(String), nullable=False, server_default="{}"),
    )
    problem_category: str | None = Field(
        default=None,
        sa_column=Column("problemCategory", String, nullable=True),
    )
