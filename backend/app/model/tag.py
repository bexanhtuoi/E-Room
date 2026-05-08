from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from app.model.common import BaseEntity


class TagCategory(StrEnum):
    TECHNOLOGY = "technology"
    BUSINESS = "business"
    SCIENCE = "science"
    CREATIVE = "creative"
    LIFESTYLE = "lifestyle"
    OTHER = "other"


class Tag(BaseEntity):
    name: str
    slug: str
    category: TagCategory = TagCategory.OTHER
    icon: str | None = None
    is_custom: bool = False
    approved: bool = True
    usage_count: int = Field(default=0, ge=0)


class UserTag(BaseEntity):
    user_id: str
    tag_id: str
