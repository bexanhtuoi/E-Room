from __future__ import annotations

from uuid import UUID

from sqlmodel import Field, JSON, Column, SQLModel

from app.model.common import AgentLevel, EnglishLevel, RoomStatus, TimestampedModel


class RoomBase(SQLModel):
    livekit_room_name: str = Field(index=True, unique=True)
    topic: str | None = None
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    primary_tag_id: UUID | None = Field(default=None, foreign_key="tags.id")
    agent_level: AgentLevel = AgentLevel.BASIC
    english_level: EnglishLevel | None = None
    status: RoomStatus = RoomStatus.IDLE
    max_participants: int = Field(default=5, ge=3, le=5)
    current_participants: int = 0
    session_duration_seconds: int = Field(default=900, ge=300, le=3600)
    is_private: bool = False
    is_public: bool = True
    creator_user_id: UUID | None = Field(default=None, foreign_key="users.id")


class Room(TimestampedModel, RoomBase, table=True):
    __tablename__ = "rooms"


class RoomParticipant(TimestampedModel, table=True):
    __tablename__ = "room_participants"

    room_id: UUID = Field(foreign_key="rooms.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    speaking_time_seconds: int = 0
    words_spoken: int = 0
    is_muted: bool = False
    connection_quality: str | None = None
