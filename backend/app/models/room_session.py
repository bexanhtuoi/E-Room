from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from app.utils.datetime_utils import now_utc


class RoomSession(SQLModel, table=True):
    __tablename__ = "sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    room_id: int = Field(foreign_key="rooms.id", index=True)
    joined_at: datetime = Field(default_factory=now_utc, nullable=False)
    left_at: Optional[datetime] = Field(default=None)
    duration_seconds: Optional[int] = Field(default=None)
    created_at: datetime = Field(default_factory=now_utc, nullable=False)

    user: Optional["User"] = Relationship(back_populates="sessions")
    room: Optional["Room"] = Relationship(back_populates="sessions")
