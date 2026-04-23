from datetime import datetime
from typing import List
from sqlalchemy import Column, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


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
