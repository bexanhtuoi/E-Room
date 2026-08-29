from __future__ import annotations

import uuid

import pytest

from app.integration.redis import (
    decr,
    delete,
    exists,
    get,
    incr,
    sadd,
    scard,
    set,
    set_if_absent,
    smembers,
    srem,
)

pytestmark = pytest.mark.requires_redis


@pytest.fixture
def redis_live(redis_available: bool):
    if not redis_available:
        pytest.skip("Redis is not available")
    return None


def unique_key(prefix: str) -> str:
    return f"test:{prefix}:{uuid.uuid4().hex[:8]}"


class TestKeyValue:
    def test_set_get_delete_roundtrip(self, redis_live):
        key = unique_key("kv")
        try:
            assert set(key, "value1") is True
            assert get(key) == "value1"
            assert exists(key) == 1
            assert delete(key) == 1
            assert get(key) is None
        finally:
            delete(key)

    def test_set_with_ttl_expires(self, redis_live):
        import time

        from app.integration.redis import get_redis_client

        key = unique_key("ttl")
        try:
            set(key, "temp", ttl=2)
            assert 0 < get_redis_client().ttl(key) <= 2
            time.sleep(0.1)
            assert get(key) == "temp"
        finally:
            delete(key)

    def test_delete_multiple_keys(self, redis_live):
        key_a = unique_key("multi")
        key_b = unique_key("multi")
        set(key_a, "a")
        set(key_b, "b")
        deleted = delete(key_a, key_b)
        assert deleted == 2


class TestCounters:
    def test_incr_and_decr(self, redis_live):
        key = unique_key("counter")
        try:
            assert incr(key) == 1
            for _ in range(4):
                incr(key)
            assert get(key) == "5"
            assert decr(key) == 4
        finally:
            delete(key)


class TestSetOperations:
    def test_sadd_srem_smembers_scard(self, redis_live):
        key = unique_key("set")
        try:
            sadd(key, "u1", "u2")
            sadd(key, "u1")
            assert scard(key) == 2
            assert smembers(key) == {"u1", "u2"}

            srem(key, "u1")
            assert scard(key) == 1
            assert smembers(key) == {"u2"}
        finally:
            delete(key)

    def test_operations_on_missing_key(self, redis_live):
        key = unique_key("missing")
        assert scard(key) == 0
        assert len(smembers(key)) == 0
        assert srem(key, "ghost") == 0


class TestSetIfAbsent:
    def test_first_write_wins(self, redis_live):
        key = unique_key("nx")
        try:
            assert set_if_absent(key, "first", ttl=30) is True
            assert set_if_absent(key, "second", ttl=30) is False
            assert get(key) == "first"
        finally:
            delete(key)


class TestSlotsLimiter:
    def test_acquire_and_release_up_to_limit(self, redis_live):
        from app.integration.redis import acquire_slot, release_slot

        slot_name = unique_key("slot")
        try:
            assert acquire_slot(slot_name, limit=2) is True
            assert acquire_slot(slot_name, limit=2) is True
            # Vượt quá limit 2
            assert acquire_slot(slot_name, limit=2) is False

            # Giải phóng 1 slot
            release_slot(slot_name)
            assert acquire_slot(slot_name, limit=2) is True
            assert acquire_slot(slot_name, limit=2) is False
        finally:
            delete(f"eroom:slots:{slot_name}")
