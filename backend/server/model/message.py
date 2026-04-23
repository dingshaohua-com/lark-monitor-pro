from sqlalchemy import Column
from sqlmodel import Field, SQLModel
from typing import Optional, Any, Dict, List
from sqlalchemy.dialects.postgresql import JSONB


class Message(SQLModel, table=True):
    id: str = Field(primary_key=True, index=True)
    type: str | None = None
    parsed_data: Dict[str, Any] = Field(# 使用 sqlalchemy.dialects.postgresql.JSONB 可以在数据库层实现高级查询
        default_factory=dict,
        sa_column=Column(JSONB)
    )
    raw_data: Dict[str, Any] = Field(# 使用 sqlalchemy.dialects.postgresql.JSONB 可以在数据库层实现高级查询
        default_factory=dict,
        sa_column=Column(JSONB)
    )