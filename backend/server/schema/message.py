from typing import Any, Dict, List
from pydantic import BaseModel, Field
from server.model.message import Message


class MessageWithReplies(BaseModel):
    """主消息 + 嵌套回复。仅用于响应序列化（orval 会据此生成前端类型）。"""

    id: str
    type: str | None = None
    parsed_data: Dict[str, Any] = Field(default_factory=dict)
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    replies: List[Message] = Field(default_factory=list, description="嵌套回复列表")
