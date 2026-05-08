from __future__ import annotations

from pydantic import Field

from app.model.common import AgentLevel, BaseEntity, EnglishLevel, RoomStatus


class Room(BaseEntity):
    livekit_room_name: str
    topic: str | None = None
    tags: list[str] = Field(default_factory=list)
    primary_tag_id: str | None = None
    agent_level: AgentLevel = AgentLevel.BASIC
    english_level: EnglishLevel | None = None
    status: RoomStatus = RoomStatus.IDLE
    max_participants: int = Field(default=5, ge=3, le=5)
    current_participants: int = Field(default=0, ge=0)
    session_duration_seconds: int = Field(default=900, ge=300, le=3600)
    is_private: bool = False
    is_public: bool = True
    creator_user_id: str | None = None


class RoomParticipant(BaseEntity):
    room_id: str
    user_id: str
    speaking_time_seconds: int = Field(default=0, ge=0)
    words_spoken: int = Field(default=0, ge=0)
    is_muted: bool = False
    connection_quality: str | None = None
