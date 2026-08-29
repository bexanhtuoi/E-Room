from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models import RoomStatus


class RoomCreateSchema(BaseModel):
    name: str
    topic: Optional[str] = None
    max_participants: int = 5


class RoomUpdateSchema(BaseModel):
    name: Optional[str] = None
    topic: Optional[str] = None
    status: Optional[RoomStatus] = None
    max_participants: Optional[int] = None


class RoomResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    topic: Optional[str] = None
    status: Optional[RoomStatus] = None
    host_id: Optional[int] = None
    max_participants: int = 5
    created_at: Optional[datetime] = None


class RoomTokenResponse(BaseModel):
    livekit_token: str
    livekit_url: str
    room_name: str
