from __future__ import annotations

from datetime import datetime

from app.model.common import BaseEntity


class RefreshToken(BaseEntity):
    user_id: str
    token_hash: str
    device_info: str | None = None
    ip_address: str | None = None
    expires_at: datetime
    revoked: bool = False
