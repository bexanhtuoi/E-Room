from __future__ import annotations

from pydantic import BaseModel, Field

from app.model.common import AgentLevel, EnglishLevel, RoomStatus


class RoomCreateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=255)
    tag_ids: list[str] = Field(min_length=1, max_length=3)
    max_participants: int = Field(default=5, ge=3, le=5)
    is_public: bool = True


class RoomMatchRequest(BaseModel):
    auto_join: bool = True


class RoomResponse(BaseModel):
    id: str
    livekit_room_name: str
    topic: str | None = None
    tags: list[str]
    agent_level: AgentLevel
    english_level: EnglishLevel | None = None
    status: RoomStatus
    max_participants: int
    current_participants: int
    is_public: bool
