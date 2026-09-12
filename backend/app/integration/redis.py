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
        socket_timeout=5,
        socket_connect_timeout=5,
        health_check_interval=30,
        retry_on_timeout=True,
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


def keys(pattern: str) -> list:
    return sorted(get_redis_client().keys(pattern))


def exists(*keys: str) -> int:
    return get_redis_client().exists(*keys)


def incr(key: str) -> int:
    return get_redis_client().incr(key)


def decr(key: str) -> int:
    return get_redis_client().decr(key)


def expire(name: str, ttl: int) -> int:
    return get_redis_client().expire(name, ttl)


def sadd(name: str, *values: str) -> int:
    return get_redis_client().sadd(name, *values)


def srem(name: str, *values: str) -> int:
    return get_redis_client().srem(name, *values)


def smembers(name: str) -> Set[str]:
    return get_redis_client().smembers(name)


def scard(name: str) -> int:
    return get_redis_client().scard(name)


COMPARE_DELETE_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""

COMPARE_REFRESH_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    redis.call('SET', KEYS[1], ARGV[1], 'EX', ARGV[2])
    return 1
end
return 0
"""

ACQUIRE_SLOT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current > tonumber(ARGV[1]) then
    redis.call('DECR', KEYS[1])
    return 0
end
redis.call('EXPIRE', KEYS[1], ARGV[2])
return 1
"""

RELEASE_SLOT_SCRIPT = """
local current = redis.call('DECR', KEYS[1])
if current <= 0 then
    redis.call('DEL', KEYS[1])
end
return 1
"""


def compare_delete(key: str, value: str) -> bool:
    client = get_redis_client()
    script = client.register_script(COMPARE_DELETE_SCRIPT)
    return bool(script(keys=[key], args=[value]))


def compare_refresh(key: str, value: str, ttl: int) -> bool:
    client = get_redis_client()
    script = client.register_script(COMPARE_REFRESH_SCRIPT)
    return bool(script(keys=[key], args=[value, ttl]))


def acquire_slot(name: str, limit: int, ttl: int = 900) -> bool:
    client = get_redis_client()
    script = client.register_script(ACQUIRE_SLOT_SCRIPT)
    result = script(keys=[f"eroom:slots:{name}"], args=[limit, ttl])
    return bool(result)


def release_slot(name: str) -> None:
    client = get_redis_client()
    script = client.register_script(RELEASE_SLOT_SCRIPT)
    script(keys=[f"eroom:slots:{name}"])
