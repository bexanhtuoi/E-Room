from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlmodel import Field, SQLModel

from app.model.common import TimestampedModel


class RefreshTokenBase(SQLModel):
    user_id: UUID = Field(foreign_key="users.id", index=True)
    token_hash: str = Field(unique=True, index=True)
    device_info: str | None = None
    ip_address: str | None = None
    expires_at: datetime
    revoked: bool = False


class RefreshToken(TimestampedModel, RefreshTokenBase, table=True):
    __tablename__ = "refresh_tokens"
