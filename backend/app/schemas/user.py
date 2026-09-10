from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, EmailStr, field_validator

from app.models import EnglishLevel, RoleEnum

MAX_RESUME_SKILLS = 20
MAX_RESUME_ENTRIES = 10
MAX_RESUME_SCHOOLS = 5


def normalize_string_list(values: Optional[List[str]], limit: int) -> List[str]:
    seen = set()
    result = []
    for item in values or []:
        name = str(item or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(name[:60])
    return result[:limit]


def normalize_entry_list(values: Optional[List[Dict[str, Any]]], limit: int, fields: List[str]) -> List[Dict[str, str]]:
    result = []
    for item in values or []:
        if not isinstance(item, dict):
            continue
        entry = {field: str(item.get(field) or "").strip()[:200] for field in fields}
        if not any(entry.values()):
            continue
        result.append(entry)
    return result[:limit]


def json_to_list(raw, limit: int) -> List[str]:
    import json

    if isinstance(raw, list):
        return normalize_string_list(raw, limit)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return []
        if isinstance(parsed, list):
            return normalize_string_list(parsed, limit)
    return []


def json_to_entries(raw, limit: int, fields: List[str]) -> List[Dict[str, str]]:
    import json

    if isinstance(raw, list):
        return normalize_entry_list(raw, limit, fields)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return []
        if isinstance(parsed, list):
            return normalize_entry_list(parsed, limit, fields)
    return []


def list_to_json(values: Optional[List[Any]]) -> str:
    import json

    return json.dumps(values or [])


EXPERIENCE_FIELDS = ["title", "company", "time", "desc"]
EDUCATION_FIELDS = ["school", "degree", "time"]


class Token(BaseModel):
    access_token: str
    token_type: str


class UserBaseSchema(BaseModel):
    email: EmailStr
    full_name: str


class UserCreateSchema(UserBaseSchema):
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isalpha() for c in v):
            raise ValueError("Password must contain at least one letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        return v


class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    email: EmailStr
    full_name: str
    avatar_url: Optional[str] = None
    english_level: Optional[EnglishLevel] = None
    role: Optional[RoleEnum] = "user"
    profile_completed: bool = False
    headline: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    skills: List[str] = []
    experience: List[Dict[str, str]] = []
    education: List[Dict[str, str]] = []
    created_at: Optional[datetime] = None

    @field_validator("skills", mode="before")
    @classmethod
    def parse_skills(cls, raw) -> List[str]:
        return json_to_list(raw, MAX_RESUME_SKILLS)

    @field_validator("experience", mode="before")
    @classmethod
    def parse_experience(cls, raw) -> List[Dict[str, str]]:
        return json_to_entries(raw, MAX_RESUME_ENTRIES, EXPERIENCE_FIELDS)

    @field_validator("education", mode="before")
    @classmethod
    def parse_education(cls, raw) -> List[Dict[str, str]]:
        return json_to_entries(raw, MAX_RESUME_SCHOOLS, EDUCATION_FIELDS)


class UserStatsResponse(BaseModel):
    messages_total: int
    messages_this_week: int
    messages_last_week: int
    week_delta: int
    streak_days: int
    most_active_day: Optional[str] = None
    most_active_day_count: int = 0


class UserUpdateSchema(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    avatar_url: Optional[str] = None
    english_level: Optional[EnglishLevel] = None
    role: Optional[Union[str, RoleEnum]] = None
    profile_completed: Optional[bool] = None
    headline: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    skills: Optional[List[str]] = None
    experience: Optional[List[Dict[str, str]]] = None
    education: Optional[List[Dict[str, str]]] = None

    @field_validator("headline", "location")
    @classmethod
    def validate_short_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        text = v.strip()
        return text[:120] if text else None

    @field_validator("bio")
    @classmethod
    def validate_bio(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        text = v.strip()
        return text[:2000] if text else None

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        text = v.strip()
        return text[:255] if text else None

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        return normalize_string_list(v, MAX_RESUME_SKILLS)

    @field_validator("experience")
    @classmethod
    def validate_experience(cls, v: Optional[List[Dict[str, str]]]) -> Optional[List[Dict[str, str]]]:
        if v is None:
            return None
        return normalize_entry_list(v, MAX_RESUME_ENTRIES, EXPERIENCE_FIELDS)

    @field_validator("education")
    @classmethod
    def validate_education(cls, v: Optional[List[Dict[str, str]]]) -> Optional[List[Dict[str, str]]]:
        if v is None:
            return None
        return normalize_entry_list(v, MAX_RESUME_SCHOOLS, EDUCATION_FIELDS)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[Union[str, RoleEnum]]) -> Optional[RoleEnum]:
        if v is None:
            return v
        if v not in RoleEnum._value2member_map_:
            raise ValueError(f"Invalid role: {v}")
        return v