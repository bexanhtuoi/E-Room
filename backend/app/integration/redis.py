import json
import time
from functools import lru_cache
from typing import Any, Optional, Set

import redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.config import settings


@lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
    return redis.Redis.from_url(
        settings.redis_url,
        decode_responses=True,
    )


def serialize(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, default=str)


def deserialize(raw: Optional[str]) -> Any:
    if raw is None:
        return None

    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


def ping() -> bool:
    try:
        return get_redis_client().ping()
    except (RedisConnectionError, RedisTimeoutError):
        return False


def get(key: str) -> Optional[str]:
    return get_redis_client().get(key)


def set(key: str, value: str, ttl: Optional[int] = None) -> bool:
    return get_redis_client().set(key, value, ex=ttl)


def set_if_absent(key: str, value: str, ttl: int) -> bool:
    created = get_redis_client().set(key, value, nx=True, ex=ttl)
    return bool(created)


def delete(*keys: str) -> int:
    return get_redis_client().delete(*keys)


def exists(*keys: str) -> int:
    return get_redis_client().exists(*keys)


def incr(key: str) -> int:
    return get_redis_client().incr(key)


def decr(key: str) -> int:
    return get_redis_client().decr(key)


def sadd(name: str, *values: str) -> int:
    return get_redis_client().sadd(name, *values)


def srem(name: str, *values: str) -> int:
    return get_redis_client().srem(name, *values)


def smembers(name: str) -> Set[str]:
    return get_redis_client().smembers(name)


def scard(name: str) -> int:
    return get_redis_client().scard(name)


ACQUIRE_SLOT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current > tonumber(ARGV[1]) then
    redis.call('DECR', KEYS[1])
    return 0
end
return 1
"""

RELEASE_SLOT_SCRIPT = """
local current = redis.call('DECR', KEYS[1])
if current <= 0 then
    redis.call('DEL', KEYS[1])
end
return 1
"""


def acquire_slot(name: str, limit: int) -> bool:
    client = get_redis_client()
    script = client.register_script(ACQUIRE_SLOT_SCRIPT)
    result = script(keys=[f"eroom:slots:{name}"], args=[limit])
    return bool(result)


def release_slot(name: str) -> None:
    client = get_redis_client()
    script = client.register_script(RELEASE_SLOT_SCRIPT)
    script(keys=[f"eroom:slots:{name}"])
