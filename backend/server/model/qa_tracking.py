from typing import Any, Dict
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class QaTracking(SQLModel, table=True):
    __tablename__ = "qa_tracking"

    feedback_id: str = Field(primary_key=True, index=True, description="反馈 ID")
    raw_data: Dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSONB, nullable=False),
    )
