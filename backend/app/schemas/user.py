from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel, EmailStr, field_validator

from app.models import EnglishLevel, RoleEnum




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
    location: Optional[str] = None
    learning_goal: Optional[str] = None
    career_field: Optional[str] = None
    interests: List[str] = []
    created_at: Optional[datetime] = None

    @field_validator("interests", mode="before")
    @classmethod
    def parse_interests(cls, raw) -> List[str]:
        import json

        if isinstance(raw, list):
            return [str(item).strip()[:60] for item in raw if str(item).strip()][:20]
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except (ValueError, TypeError):
                return []
            if isinstance(parsed, list):
                return [str(item).strip()[:60] for item in parsed if str(item).strip()][:20]
        return []


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
    location: Optional[str] = None
    learning_goal: Optional[str] = None
    career_field: Optional[str] = None
    interests: Optional[List[str]] = None

    @field_validator("career_field")
    @classmethod
    def validate_career_field(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        text = v.strip()
        return text[:120] if text else None

    @field_validator("interests")
    @classmethod
    def validate_interests(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        return [str(item).strip()[:60] for item in v if str(item).strip()][:20]

    @field_validator("learning_goal")
    @classmethod
    def validate_learning_goal(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        text = v.strip()
        return text[:500] if text else None

    @field_validator("headline", "location")
    @classmethod
    def validate_short_text(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        text = v.strip()
        return text[:120] if text else None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[Union[str, RoleEnum]]) -> Optional[RoleEnum]:
        if v is None:
            return v
        if v not in RoleEnum._value2member_map_:
            raise ValueError(f"Invalid role: {v}")
        return v