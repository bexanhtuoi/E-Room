from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlmodel import Column, Field, Relationship, SQLModel, String, Text

from app.utils.datetime_utils import now_utc


class DocumentKind(StrEnum):
    # file: tai lieu upload (MinIO + vector) | skill: doan prompt nap vao agent
    FILE = "file"
    SKILL = "skill"


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    room_id: Optional[int] = Field(default=None, foreign_key="rooms.id", index=True)
    kind: DocumentKind = Field(default=DocumentKind.FILE)
    file_name: str = Field(...)
    file_type: str = Field(...)
    file_path: str = Field(...)
    content: Optional[str] = Field(default=None, sa_column=Column(Text))
    enabled: bool = Field(default=True)
    metadata_json: Optional[str] = Field(default=None, sa_column=Column(String(4000)))
    created_at: datetime = Field(default_factory=now_utc, nullable=False)
    updated_at: datetime = Field(default_factory=now_utc, nullable=False)

    user: "User" = Relationship(back_populates="documents")