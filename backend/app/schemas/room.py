from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

from app.models import RoomStatus

MAX_TOPICS_PER_ROOM = 5
MAX_SEATS_PER_ROOM = 4


def normalize_topic_name(value: str) -> str:
    words = str(value or "").strip().split()
    normalized = [word if not word.islower() else word[:1].upper() + word[1:] for word in words]
    return " ".join(normalized)


def normalize_topic_list(values: Optional[List[str]]) -> List[str]:
    seen = set()
    result = []
    for item in values or []:
        name = normalize_topic_name(item)
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(name)
    if len(result) > MAX_TOPICS_PER_ROOM:
        raise ValueError(f"A room can have at most {MAX_TOPICS_PER_ROOM} topics")
    return result


def topics_to_json(values: Optional[List[str]]) -> str:
    import json

    return json.dumps(normalize_topic_list(values))


def topics_from_json(raw) -> List[str]:
    import json

    if isinstance(raw, list):
        return normalize_topic_list(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return []
        if isinstance(parsed, list):
            return [str(item) for item in parsed if str(item).strip()]
    return []


class RoomCreateSchema(BaseModel):
    name: str
    topics: List[str] = []
    description: Optional[str] = None
    max_participants: int = 4

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Room name must not be empty")
        return text[:120]

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, values: List[str]) -> List[str]:
        return normalize_topic_list(values)

    @field_validator("max_participants")
    @classmethod
    def validate_seats(cls, value: int) -> int:
        if value < 1 or value > MAX_SEATS_PER_ROOM:
            raise ValueError(f"Seats must be between 1 and {MAX_SEATS_PER_ROOM}")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = value.strip()
        return text[:2000] if text else None


class RoomUpdateSchema(BaseModel):
    name: Optional[str] = None
    topics: Optional[List[str]] = None
    description: Optional[str] = None
    status: Optional[RoomStatus] = None
    max_participants: Optional[int] = None
    enable_heartbeat: Optional[bool] = None
    enable_transcript: Optional[bool] = None
    enable_agent: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("Room name must not be empty")
        return text[:120]

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, values: Optional[List[str]]) -> Optional[List[str]]:
        if values is None:
            return None
        return normalize_topic_list(values)

    @field_validator("max_participants")
    @classmethod
    def validate_seats(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return None
        if value < 1 or value > MAX_SEATS_PER_ROOM:
            raise ValueError(f"Seats must be between 1 and {MAX_SEATS_PER_ROOM}")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = value.strip()
        return text[:2000] if text else None


class RoomResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    name: str
    topics: List[str] = []
    description: Optional[str] = None
    status: Optional[RoomStatus] = None
    host_id: Optional[int] = None
    max_participants: int = 4
    enable_heartbeat: bool = True
    enable_transcript: bool = True
    enable_agent: bool = True
    created_at: Optional[datetime] = None

    @field_validator("topics", mode="before")
    @classmethod
    def parse_topics(cls, raw) -> List[str]:
        return topics_from_json(raw)


class RoomTokenResponse(BaseModel):
    livekit_token: str
    livekit_url: str
    room_name: str


class RoomMatchRequest(BaseModel):
    topic: Optional[str] = None


class RoomMatchResponse(BaseModel):
    status: str
    room: Optional[RoomResponse] = None
