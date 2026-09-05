from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlmodel import Column, Field, Relationship, SQLModel, String

from app.utils.datetime_utils import now_utc


class RoomStatus(StrEnum):
    # 3 trang thai: live (co nguoi) - open (trong) - ended (chet)
    IDLE = "idle"
    ACTIVE = "active"
    ENDED = "ended"


class Room(SQLModel, table=True):
    __tablename__ = "rooms"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True)
    topics: str = Field(default="[]", sa_column=Column(String(2000), nullable=False))
    description: Optional[str] = Field(default=None, sa_column=Column(String(2000)))
    status: Optional[RoomStatus] = Field(default=RoomStatus.IDLE)
    host_id: Optional[int] = Field(default=None, foreign_key="users.id")
    max_participants: int = Field(default=4, ge=1)
    enable_heartbeat: bool = Field(default=True)
    enable_transcript: bool = Field(default=True)
    enable_agent: bool = Field(default=True)
    created_at: datetime = Field(default_factory=now_utc, nullable=False)
    updated_at: datetime = Field(default_factory=now_utc, nullable=False)

    host: Optional["User"] = Relationship(back_populates="rooms")
    messages: list["Message"] = Relationship(back_populates="room")
