from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RoomCreateRequest(BaseModel):
    topic: str = Field(min_length=3, max_length=200)
    tag_ids: list[str] = Field(default_factory=list)
    max_participants: int = Field(default=5, ge=2, le=50)
    is_public: bool = True


class RoomJoinRequest(BaseModel):
    user_id: str


class RoomMatchRequest(BaseModel):
    user_id: str
    tag_ids: list[str] = Field(default_factory=list)


class RoomResponse(BaseModel):
    id: str
    livekit_room_name: str
    topic: str
    tags: list[str] = Field(default_factory=list)
    agent_level: str = "basic"
    english_level: str = "any"
    status: str = "MATCHING"
    max_participants: int = 5
    current_participants: int = 0
    is_public: bool = True


class RoomDetailResponse(RoomResponse):
    participants: list[str] = Field(default_factory=list)
    messages: list[dict] = Field(default_factory=list)


class RoomTokenResponse(BaseModel):
    room_id: str
    room_name: str
    livekit_token: str
    livekit_url: str
