from __future__ import annotations

from pydantic import Field

from app.model.common import BaseEntity, MessageType


class Message(BaseEntity):
    room_id: str
    user_id: str | None = None
    content: str
    message_type: MessageType = MessageType.TEXT
    metadata: dict[str, str | int | float | bool | list[str] | None] = Field(default_factory=dict)
