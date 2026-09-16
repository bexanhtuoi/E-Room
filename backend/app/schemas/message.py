from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models import MessageRole

MAX_MESSAGE_TEXT_LENGTH = 4000


def clean_message_text(value: str) -> str:
    text = (value or "").strip()

    if not text:
        raise ValueError("Message text must not be empty")

    if len(text) > MAX_MESSAGE_TEXT_LENGTH:
        raise ValueError(f"Message text must be at most {MAX_MESSAGE_TEXT_LENGTH} characters")

    return text


class MessageCreateSchema(BaseModel):
    room_id: int
    text: str
    role: Optional[MessageRole] = MessageRole.USER
    meta_data: Optional[str] = None

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        return clean_message_text(value)


class MessageResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    room_id: int
    user_id: Optional[int] = None
    role: MessageRole
    text: str
    meta_data: Optional[str] = None
    created_at: Optional[datetime] = None
