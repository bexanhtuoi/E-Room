from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.model.common import TimestampedModel


class TagCategory(StrEnum):
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    SCIENCE = "science"
    CREATIVE = "creative"
    LIFESTYLE = "lifestyle"
    OTHER = "other"


class TagBase(SQLModel):
    name: str = Field(index=True, unique=True)
    slug: str = Field(index=True, unique=True)
    category: TagCategory = TagCategory.OTHER
    icon: str | None = None
    is_custom: bool = False
    approved: bool = True
    usage_count: int = 0


class Tag(TimestampedModel, TagBase, table=True):
    __tablename__ = "tags"


class UserTag(TimestampedModel, table=True):
    __tablename__ = "user_tags"

    user_id: UUID = Field(foreign_key="users.id", index=True)
    tag_id: UUID = Field(foreign_key="tags.id", index=True)
