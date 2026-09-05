from datetime import datetime
from typing import Optional, Union

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
    created_at: Optional[datetime] = None


class UserUpdateSchema(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    avatar_url: Optional[str] = None
    english_level: Optional[EnglishLevel] = None
    role: Optional[Union[str, RoleEnum]] = None
    profile_completed: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[Union[str, RoleEnum]]) -> Optional[RoleEnum]:
        if v is None:
            return v
        if v not in RoleEnum._value2member_map_:
            raise ValueError(f"Invalid role: {v}")
        return v