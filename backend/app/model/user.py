from __future__ import annotations

from pydantic import EmailStr

from app.model.common import BaseEntity, EnglishLevel


class User(BaseEntity):
    email: EmailStr
    password_hash: str | None = None
    display_name: str
    avatar_url: str | None = None
    english_level: EnglishLevel | None = None
    career_field: str | None = None
    job_title: str | None = None
    learning_goal: str | None = None
    auto_join_enabled: bool = True
    profile_completed: bool = False
    email_verified: bool = False
    is_active: bool = True
    is_banned: bool = False
    ban_reason: str | None = None
    strikes: int = 0
