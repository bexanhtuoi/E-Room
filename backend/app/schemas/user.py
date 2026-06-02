from __future__ import annotations

from pydantic import BaseModel, EmailStr

from app.model.common import EnglishLevel


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    first_name: str
    last_name: str
    display_name: str
    english_level: EnglishLevel | None = None
    learning_goal: str | None = None
    profile_completed: bool = False
    is_admin: bool = False
    is_superuser: bool = False


class UserProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    english_level: EnglishLevel | None = None
    learning_goal: str | None = None
    profile_completed: bool | None = None
