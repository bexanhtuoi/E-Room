from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models import MessageRole


class MessageCreateSchema(BaseModel):
    room_id: int
    text: str
    role: Optional[MessageRole] = MessageRole.USER
    meta_data: Optional[str] = None


class MessageResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    room_id: int
    user_id: Optional[int] = None
    role: MessageRole
    text: str
    meta_data: Optional[str] = None
    created_at: Optional[datetime] = None
