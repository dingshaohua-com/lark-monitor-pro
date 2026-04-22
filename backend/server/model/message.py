from sqlmodel import Field, SQLModel

class Message(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    content: str | None = None