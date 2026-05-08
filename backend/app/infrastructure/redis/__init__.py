from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Optional

import redis

from app.config import settings


@lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)


class RedisCRUD:
    def __init__(self, client: redis.Redis) -> None:
        self._client = client

    def get(self, key: str) -> Optional[str]:
        return self._client.get(key)

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        return self._client.set(key, value, ex=ttl)

    def delete(self, *keys: str) -> int:
        return self._client.delete(*keys)

    def exists(self, *keys: str) -> int:
        return self._client.exists(*keys)

    def get_json(self, key: str) -> Optional[Any]:
        raw = self._client.get(key)
        if raw is None:
            return None
        return json.loads(raw)

    def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        return self._client.set(key, json.dumps(value, default=str), ex=ttl)

    def hget(self, name: str, key: str) -> Optional[str]:
        return self._client.hget(name, key)

    def hset(self, name: str, key: str, value: str) -> int:
        return self._client.hset(name, key, value)

    def hgetall(self, name: str) -> dict[str, str]:
        return self._client.hgetall(name)

    def sadd(self, name: str, *values: str) -> int:
        return self._client.sadd(name, *values)

    def smembers(self, name: str) -> set[str]:
        return self._client.smembers(name)

    def srem(self, name: str, *values: str) -> int:
        return self._client.srem(name, *values)

    def publish(self, channel: str, message: Any) -> int:
        payload = message if isinstance(message, (str, bytes)) else json.dumps(message, default=str)
        return self._client.publish(channel, payload)

    def ping(self) -> bool:
        try:
            return self._client.ping()
        except Exception:
            return False

    def keys(self, pattern: str = "*") -> list[str]:
        return self._client.keys(pattern)
