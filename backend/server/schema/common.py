from datetime import date
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class SyncRequest(BaseModel):
    """同步请求体"""
    mode: str = Field("continue", description="continue=从上次继续, range=指定时间段")
    start: Optional[date] = Field(None, description="起始日期 YYYY-MM-DD")
    end: Optional[date] = Field(None, description="结束日期 YYYY-MM-DD")


class Page(BaseModel, Generic[T]):
    """通用分页响应"""
    items: List[T] = Field(default_factory=list, description="当前页数据")
    total: int = Field(0, description="总条数")
    page: int = Field(1, description="当前页码，从 1 开始")
    pageSize: int = Field(20, description="每页条数")