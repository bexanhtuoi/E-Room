from __future__ import annotations

import json
import os

import pytest

from app.infrastructure.redis_client import (
    RedisCRUD,
    RateLimiter,
    _deserialize,
    _serialize,
)
from app.config import settings


class TestSerialize:
    def test_serialize_string_returns_same(self) -> None:
        result = _serialize("hello world")
        assert result == "hello world"

    def test_serialize_dict_returns_json(self) -> None:
        result = _serialize({"key": "value", "num": 42})
        parsed = json.loads(result)
        assert parsed == {"key": "value", "num": 42}

    def test_serialize_list_returns_json(self) -> None:
        result = _serialize([1, 2, 3])
        parsed = json.loads(result)
        assert parsed == [1, 2, 3]

    def test_serialize_none_returns_null_string(self) -> None:
        result = _serialize(None)
        assert result == "null"

    def test_serialize_int_returns_string(self) -> None:
        result = _serialize(42)
        assert result == "42"

    def test_serialize_bool_returns_string(self) -> None:
        result = _serialize(True)
        assert result == "true"


class TestDeserialize:
    def test_deserialize_none_returns_none(self) -> None:
        result = _deserialize(None)
        assert result is None

    def test_deserialize_json_object(self) -> None:
        result = _deserialize('{"a": 1, "b": 2}')
        assert result == {"a": 1, "b": 2}

    def test_deserialize_json_array(self) -> None:
        result = _deserialize('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_deserialize_json_null(self) -> None:
        result = _deserialize("null")
        assert result is None

    def test_deserialize_plain_string_returns_as_is(self) -> None:
        result = _deserialize("not-json-at-all")
        assert result == "not-json-at-all"

    def test_deserialize_empty_string_returns_as_is(self) -> None:
        result = _deserialize("")
        assert result == ""

    def test_deserialize_json_number_returns_number(self) -> None:
        result = _deserialize("42")
        assert result == 42

    def test_serialize_deserialize_roundtrip(self) -> None:
        original = {"user_id": 1, "name": "test", "tags": ["a", "b"]}
        serialized = _serialize(original)
        deserialized = _deserialize(serialized)
        assert deserialized == original


class TestRedisCRUDStructure:
    def test_init_without_client_uses_default(self) -> None:
        crud = RedisCRUD()
        assert crud._client is not None

    def test_init_with_custom_client(self) -> None:
        import redis as redis_lib
        client = redis_lib.Redis.from_url("redis://localhost:6379/0", decode_responses=True)
        crud = RedisCRUD(client)
        assert crud._client is client


@pytest.mark.skipif(not os.getenv("CI"), reason="Requires Redis server")
class TestRedisCRUDIntegration:
    def test_set_and_get_roundtrip(self) -> None:
        crud = RedisCRUD()
        crud.set("test_key", "test_value", ttl=60)
        result = crud.get("test_key")
        assert result == "test_value"
        crud.delete("test_key")

    def test_exists_returns_true_for_existing_key(self) -> None:
        crud = RedisCRUD()
        crud.set("test_exists", "1", ttl=60)
        assert crud.exists("test_exists") > 0
        crud.delete("test_exists")

    def test_exists_returns_zero_for_missing_key(self) -> None:
        crud = RedisCRUD()
        assert crud.exists("nonexistent_key_xyz") == 0

    def test_delete_removes_key(self) -> None:
        crud = RedisCRUD()
        crud.set("test_delete", "value", ttl=60)
        crud.delete("test_delete")
        assert crud.exists("test_delete") == 0

    def test_setnx_acquires_lock_once(self) -> None:
        crud = RedisCRUD()
        key = "test_setnx_lock"
        assert crud.setnx(key, "1", ttl=5) is True
        assert crud.setnx(key, "1", ttl=5) is False
        crud.delete(key)

    def test_incr_and_decr(self) -> None:
        crud = RedisCRUD()
        key = "test_counter"
        crud.delete(key)
        assert crud.incr(key) == 1
        assert crud.incr(key, 5) == 6
        assert crud.decr(key, 3) == 3
        crud.delete(key)

    def test_get_json_and_set_json_roundtrip(self) -> None:
        crud = RedisCRUD()
        data = {"name": "user", "count": 5}
        crud.set_json("test_json", data, ttl=60)
        result = crud.get_json("test_json")
        assert result == data
        crud.delete("test_json")

    def test_publish_and_subscribe(self) -> None:
        crud = RedisCRUD()
        pubsub = crud.pubsub()
        pubsub.subscribe("test_channel")
        crud.publish("test_channel", {"msg": "hello"})
        pubsub.close()

    def test_hset_and_hget(self) -> None:
        crud = RedisCRUD()
        crud.hset("test_hash", "field1", "value1")
        assert crud.hget("test_hash", "field1") == "value1"
        crud.delete("test_hash")

    def test_sadd_and_smembers(self) -> None:
        crud = RedisCRUD()
        crud.sadd("test_set", "a", "b", "c")
        members = crud.smembers("test_set")
        assert members == {"a", "b", "c"}
        crud.delete("test_set")

    def test_zadd_and_zrange(self) -> None:
        crud = RedisCRUD()
        crud.zadd("test_zset", {"a": 1.0, "b": 2.0, "c": 3.0})
        result = crud.zrange("test_zset", 0, -1, withscores=True)
        assert len(result) == 3
        crud.delete("test_zset")

    def test_rate_limit_allows_within_window(self) -> None:
        crud = RedisCRUD()
        key = "test_ratelimit"
        crud.delete(key)
        allowed, remaining = crud.rate_limit(key, max_requests=3, window_seconds=10)
        assert allowed is True
        assert remaining == 2
        crud.delete(key)

    def test_rate_limit_blocks_after_max(self) -> None:
        crud = RedisCRUD()
        key = "test_ratelimit_block"
        crud.delete(key)
        crud.rate_limit(key, max_requests=2, window_seconds=10)
        crud.rate_limit(key, max_requests=2, window_seconds=10)
        allowed, remaining = crud.rate_limit(key, max_requests=2, window_seconds=10)
        assert allowed is False
        assert remaining == 0
        crud.delete(key)


@pytest.mark.skipif(not os.getenv("CI"), reason="Requires Redis server")
class TestRateLimiterIntegration:
    def test_check_returns_allowed_and_remaining(self) -> None:
        limiter = RateLimiter()
        allowed, remaining = limiter.check("test_user", "endpoint", max_requests=5)
        assert isinstance(allowed, bool)
        assert isinstance(remaining, int)

    def test_check_login_uses_login_endpoint(self) -> None:
        limiter = RateLimiter()
        allowed, remaining = limiter.check_login("192.168.1.1")
        assert isinstance(allowed, bool)
        assert isinstance(remaining, int)

    def test_check_tts_uses_user_session(self) -> None:
        limiter = RateLimiter()
        allowed, remaining = limiter.check_tts("user123", "session456")
        assert isinstance(allowed, bool)
        assert isinstance(remaining, int)
