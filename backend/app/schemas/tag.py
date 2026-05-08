from __future__ import annotations

from pydantic import BaseModel, Field

from app.model.tag import TagCategory


class TagResponse(BaseModel):
    id: str
    name: str
    slug: str
    category: TagCategory
    usage_count: int = 0


class CustomTagCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: TagCategory = TagCategory.OTHER


class UserTagBulkAddRequest(BaseModel):
    tag_ids: list[str] = Field(min_length=1, max_length=10)
