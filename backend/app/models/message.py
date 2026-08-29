from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlmodel import Column, Field, Relationship, SQLModel, String

from app.utils.datetime_utils import now_utc


class MessageRole(StrEnum):
    USER = "user"
    AI = "ai"


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    room_id: int = Field(foreign_key="rooms.id")
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    role: MessageRole = Field(default=MessageRole.USER)
    text: str = Field(sa_column=Column(String(4000)))
    meta_data: Optional[str] = Field(default=None, sa_column=Column(String(4000)))
    created_at: datetime = Field(default_factory=now_utc, nullable=False)

    room: "Room" = Relationship(back_populates="messages")
    user: Optional["User"] = Relationship(back_populates="messages")
