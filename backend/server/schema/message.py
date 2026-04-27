from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field
from server.model.message import Message


class MessageWithReplies(BaseModel):
    """主消息 + 嵌套回复。仅用于响应序列化（orval 会据此生成前端类型）。"""

    id: str
    type: str | None = None
    parsed_data: Dict[str, Any] = Field(default_factory=dict)
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    replies: List[Message] = Field(default_factory=list, description="嵌套回复列表")


class MessageListFilter(BaseModel):
    """主消息列表查询参数（仅 list 场景，不含 id/withReply）。

    字段内部用 snake_case，对外（query 参数 / OpenAPI）通过 alias 暴露为 camelCase，
    与前端 orval 生成的类型保持一致。
    """

    model_config = ConfigDict(populate_by_name=True)

    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int | None = Field(
        default=None, alias="pageSize", ge=1, le=10000,
        description="每页条数。不传则不分页，返回全部（导出场景用）",
    )
    keyword: str | None = Field(default=None, description="按用户原文模糊搜索")
    problem_category: str | None = Field(
        default=None, alias="problemCategory", description="按机器人问题分类过滤",
    )
    start_date: str | None = Field(
        default=None, alias="startDate", description="反馈起始日期 YYYY-MM-DD（含）",
    )
    end_date: str | None = Field(
        default=None, alias="endDate", description="反馈结束日期 YYYY-MM-DD（含）",
    )
    has_bot_processed: str | None = Field(
        default=None, alias="hasBotProcessed", description="机器人是否处理过：yes / no",
    )
    duty_user: str | None = Field(
        default=None, alias="dutyUser", description="按值班人模糊匹配（关联 duty_schedule 表）",
    )
    has_qa_tracking: str | None = Field(
        default=None, alias="hasQaTracking", description="问题原因是否已跟进：yes / no",
    )


class MessageListQuery(MessageListFilter):
    """工单列表 HTTP query 参数 = 过滤项 + with_reply。

    单独抽出来是为了绕开 FastAPI 0.136 的坑：当 `Annotated[Model, Query()]`
    旁边还存在其他独立 `Query()` 参数时，模型字段的 alias 不会生效。
    把所有 query 参数收进同一个模型，就能正常使用 camelCase alias。
    """

    with_reply: bool = Field(
        default=False, alias="withReply",
        description="为 true 时同时返回主消息下 raw_data.parent_id 指向主消息 id 的回复",
    )
