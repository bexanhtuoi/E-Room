from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.schemas.room import RoomResponse


class SessionResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    room_id: int
    joined_at: datetime
    left_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    created_at: Optional[datetime] = None


class SessionWithRoom(BaseModel):
    session: SessionResponse
    room: Optional[RoomResponse] = None
    message_count: int = 0


class SessionAskRequest(BaseModel):
    question: str


class SessionAnswerResponse(BaseModel):
    answer: str
    message_count: int = 0


class SessionSummaryResponse(BaseModel):
    summary: str
    message_count: int = 0


class MySessionsResponse(BaseModel):
    sessions: List[SessionWithRoom] = []
