from datetime import date
from sqlmodel import Field, SQLModel


class DutySchedule(SQLModel, table=True):
    __tablename__ = "duty_schedule"

    duty_date: date = Field(primary_key=True, description="值班日期")
    duty_user: str = Field(description="值班人")
