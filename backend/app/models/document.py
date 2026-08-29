from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel

from app.utils.datetime_utils import now_utc


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    file_name: str = Field(...)
    file_type: str = Field(...)
    file_path: str = Field(...)
    metadata_json: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=now_utc, nullable=False)
    updated_at: datetime = Field(default_factory=now_utc, nullable=False)

    user: "User" = Relationship(back_populates="documents")