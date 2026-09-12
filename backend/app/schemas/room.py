from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator

from app.models import RoomStatus

MAX_TOPICS_PER_ROOM = 5
MAX_SEATS_PER_ROOM = 6


def normalize_topic_name(value: str) -> str:
    words = str(value or "").strip().split()
    normalized = [word if not word.islower() else word[:1].upper() + word[1:] for word in words]
    return " ".join(normalized)


def dedupe_str_list(values, clean, limit: int = 0) -> List[str]:
    seen = set()
    result = []
    for item in values or []:
        name = clean(item)
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(name)
    return result[:limit] if limit else result


def normalize_topic_list(values: Optional[List[str]]) -> List[str]:
    result = dedupe_str_list(values, normalize_topic_name)
    if len(result) > MAX_TOPICS_PER_ROOM:
        raise ValueError(f"A room can have at most {MAX_TOPICS_PER_ROOM} topics")
    return result


def topics_to_json(values: Optional[List[str]]) -> str:
    import json

    return json.dumps(normalize_topic_list(values))


SPOKEN_LANGUAGES = ("en", "vi", "auto")


def normalize_language(value) -> str:
    text = str(value or "").strip().lower()
    return text if text in SPOKEN_LANGUAGES else "en"


MAX_ROOM_EMAILS = 50


def normalize_email(item) -> str:
    email = str(item or "").strip().lower()
    return email if "@" in email else ""


def normalize_email_list(values: Optional[List[str]]) -> List[str]:
    return dedupe_str_list(values, normalize_email, MAX_ROOM_EMAILS)


def emails_to_json(values: Optional[List[str]]) -> str:
    import json

    return json.dumps(normalize_email_list(values))


def emails_from_json(raw) -> List[str]:
    import json

    if isinstance(raw, list):
        return normalize_email_list(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return []
        if isinstance(parsed, list):
            return normalize_email_list(parsed)
    return []


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


def clean_name(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = value.strip()
    if not text:
        raise ValueError("Room name must not be empty")
    return text[:120]


def clean_text(value: Optional[str], limit: int) -> Optional[str]:
    if value is None:
        return None
    text = value.strip()
    return text[:limit] if text else None


def clean_seats(value: Optional[int]) -> Optional[int]:
    if value is None:
        return None
    if value < 1 or value > MAX_SEATS_PER_ROOM:
        raise ValueError(f"Seats must be between 1 and {MAX_SEATS_PER_ROOM}")
    return value


def clean_topics(values) -> Optional[List[str]]:
    return None if values is None else normalize_topic_list(values)


def clean_emails(values) -> Optional[List[str]]:
    return None if values is None else normalize_email_list(values)


class RoomCreateSchema(BaseModel):
    name: str
    topics: List[str] = []
    description: Optional[str] = None
    max_participants: int = 4
    is_private: bool = False
    language: str = "en"
    allowed_emails: List[str] = []
    system_prompt: Optional[str] = None
    scheduled_at: Optional[datetime] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return clean_name(value)

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, values: List[str]) -> List[str]:
        return normalize_topic_list(values)

    @field_validator("max_participants")
    @classmethod
    def validate_seats(cls, value: int) -> int:
        return clean_seats(value)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: Optional[str]) -> Optional[str]:
        return clean_text(value, 2000)

    @field_validator("allowed_emails")
    @classmethod
    def validate_emails(cls, values: List[str]) -> List[str]:
        return normalize_email_list(values)

    @field_validator("system_prompt")
    @classmethod
    def validate_system_prompt(cls, value: Optional[str]) -> Optional[str]:
        return clean_text(value, 4000)

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        return normalize_language(value)


class RoomUpdateSchema(BaseModel):
    name: Optional[str] = None
    topics: Optional[List[str]] = None
    description: Optional[str] = None
    status: Optional[RoomStatus] = None
    max_participants: Optional[int] = None
    enable_heartbeat: Optional[bool] = None
    enable_transcript: Optional[bool] = None
    enable_agent: Optional[bool] = None
    is_private: Optional[bool] = None
    language: Optional[str] = None
    allowed_emails: Optional[List[str]] = None
    system_prompt: Optional[str] = None
    scheduled_at: Optional[datetime] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        return clean_name(value)

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, values: Optional[List[str]]) -> Optional[List[str]]:
        return clean_topics(values)

    @field_validator("max_participants")
    @classmethod
    def validate_seats(cls, value: Optional[int]) -> Optional[int]:
        return clean_seats(value)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: Optional[str]) -> Optional[str]:
        return clean_text(value, 2000)

    @field_validator("allowed_emails")
    @classmethod
    def validate_update_emails(cls, values: Optional[List[str]]) -> Optional[List[str]]:
        return clean_emails(values)

    @field_validator("system_prompt")
    @classmethod
    def validate_update_system_prompt(cls, value: Optional[str]) -> Optional[str]:
        return clean_text(value, 4000)

    @field_validator("language")
    @classmethod
    def validate_update_language(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return normalize_language(value)


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
    is_private: bool = False
    language: str = "en"
    allowed_emails: List[str] = []
    system_prompt: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    @field_validator("topics", mode="before")
    @classmethod
    def parse_topics(cls, raw) -> List[str]:
        return topics_from_json(raw)

    @field_validator("allowed_emails", mode="before")
    @classmethod
    def parse_emails(cls, raw) -> List[str]:
        return emails_from_json(raw)


class RoomTokenResponse(BaseModel):
    livekit_token: str
    livekit_url: str
    room_name: str


class RoomMatchRequest(BaseModel):
    topic: Optional[str] = None


class RoomMatchResponse(BaseModel):
    status: str
    room: Optional[RoomResponse] = None
