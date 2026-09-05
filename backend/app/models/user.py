from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel

from app.utils.datetime_utils import now_utc


class EnglishLevel(StrEnum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class RoleEnum(StrEnum):
    admin = "admin"
    user = "user"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: EmailStr = Field(unique=True, index=True)
    password_hash: Optional[str] = Field(default=None)
    full_name: str = Field(...)
    avatar_url: Optional[str] = Field(default=None)
    english_level: Optional[EnglishLevel] = Field(default=None)
    role: Optional[RoleEnum] = Field(default=RoleEnum.user)
    profile_completed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=now_utc, nullable=False)
    updated_at: datetime = Field(default_factory=now_utc, nullable=False)

    rooms: list["Room"] = Relationship(back_populates="host")
    messages: list["Message"] = Relationship(back_populates="user")
    notifications: list["Notification"] = Relationship(back_populates="user")
    documents: list["Document"] = Relationship(back_populates="user")
