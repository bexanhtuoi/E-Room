from __future__ import annotations

from pydantic import BaseModel, Field

from app.model.common import MessageType


class MessageCreateRequest(BaseModel):
    room_id: str
    content: str = Field(min_length=1)


class TranscriptCreateRequest(BaseModel):
    room_id: str
    user_id: str
    content: str = Field(min_length=1)


class MessageResponse(BaseModel):
    id: str
    room_id: str
    user_id: str | None = None
    content: str
    message_type: MessageType
    payload: dict = Field(default_factory=dict)
