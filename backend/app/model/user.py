from __future__ import annotations

from pydantic import EmailStr
from sqlmodel import Field, SQLModel

from app.model.common import EnglishLevel, TimestampedModel


class UserBase(SQLModel):
    email: EmailStr = Field(index=True, unique=True)
    password_hash: str | None = None
    display_name: str = Field(index=True)
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


class User(TimestampedModel, UserBase, table=True):
    __tablename__ = "users"
