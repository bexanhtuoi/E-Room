from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator

from app.models import DocumentKind


class DocumentCreateSchema(BaseModel):
    file_name: str
    file_type: str
    file_path: str
    metadata_json: Optional[str] = None


class DocumentUpdateSchema(BaseModel):
    file_name: Optional[str] = None
    metadata_json: Optional[str] = None


class RoomSkillCreateSchema(BaseModel):
    name: str
    prompt: str
    enabled: bool = True

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Skill name must not be empty")
        return text[:120]

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("Skill prompt must not be empty")
        return text[:4000]


class RoomSkillUpdateSchema(BaseModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    enabled: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("Skill name must not be empty")
        return text[:120]

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        text = value.strip()
        if not text:
            raise ValueError("Skill prompt must not be empty")
        return text[:4000]


class DocumentResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: int
    user_id: int
    room_id: Optional[int] = None
    kind: DocumentKind = DocumentKind.FILE
    file_name: str
    file_type: str
    file_path: str
    content: Optional[str] = None
    enabled: bool = True
    metadata_json: Optional[str] = None
    created_at: Optional[datetime] = None
