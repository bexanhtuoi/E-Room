from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from app.utils.datetime_utils import now_utc


class RoomStatus(StrEnum):
    IDLE = "idle"
    MATCHING = "matching"
    ACTIVE = "active"
    ENDED = "ended"


class Room(SQLModel, table=True):
    __tablename__ = "rooms"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    topic: Optional[str] = Field(default=None)
    status: Optional[RoomStatus] = Field(default=RoomStatus.IDLE)
    host_id: Optional[int] = Field(default=None, foreign_key="users.id")
    max_participants: int = Field(default=5, ge=1)
    created_at: datetime = Field(default_factory=now_utc, nullable=False)
    updated_at: datetime = Field(default_factory=now_utc, nullable=False)

    host: Optional["User"] = Relationship(back_populates="rooms")
    messages: list["Message"] = Relationship(back_populates="room")
