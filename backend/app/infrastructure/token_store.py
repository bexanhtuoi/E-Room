from __future__ import annotations

from datetime import timedelta

from app.infrastructure.redis import get_redis_client


class TokenStore:
    def __init__(self) -> None:
        self.redis = get_redis_client()

    def blacklist_access_token(self, token_hash: str, ttl_seconds: int) -> None:
        self.redis.setex(f"e-room:token:blacklist:{token_hash}", ttl_seconds, "1")

    def is_blacklisted(self, token_hash: str) -> bool:
        return bool(self.redis.exists(f"e-room:token:blacklist:{token_hash}"))
