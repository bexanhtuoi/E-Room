from __future__ import annotations

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=10, ge=1)
    total: int = Field(default=0, ge=0)


class PaginatedResponse[T](BaseModel):
    items: list[T]
    pagination: PaginationMeta


class ApiMessage(BaseModel):
    message: str
