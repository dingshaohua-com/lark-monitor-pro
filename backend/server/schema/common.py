from datetime import date
from typing import Optional
from pydantic import BaseModel, Field

class SyncRequest(BaseModel):
    """同步请求体"""
    mode: str = Field("continue", description="continue=从上次继续, range=指定时间段")
    start: Optional[date] = Field(None, description="起始日期 YYYY-MM-DD")
    end: Optional[date] = Field(None, description="结束日期 YYYY-MM-DD")