from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException, Request

from app.config import settings
from app.integration.redis import delete as redis_delete
from app.integration.redis import ping
from app.utils.rate_limit import RATE_LIMIT_PREFIX, check_rate_limit


def make_request(ip: str) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/v1/auth/login",
        "headers": [(b"x-forwarded-for", ip.encode())],
        "client": ("127.0.0.1", 5000),
    }
    return Request(scope)


@pytest.fixture
def enabled_limiter():
    if not ping():
        pytest.skip("Redis is not available")

    previous = settings.rate_limit_enabled
    settings.rate_limit_enabled = True
    try:
        yield
    finally:
        settings.rate_limit_enabled = previous


class TestRateLimit:
    def test_allows_then_blocks(self, enabled_limiter):
        scope = f"test-{uuid.uuid4().hex[:8]}"
        request = make_request("10.9.9.1")

        try:
            for _ in range(3):
                check_rate_limit(request, scope, 3, 60)

            with pytest.raises(HTTPException) as raised:
                check_rate_limit(request, scope, 3, 60)

            assert raised.value.status_code == 429
        finally:
            redis_delete(f"{RATE_LIMIT_PREFIX}:{scope}:10.9.9.1")

    def test_disabled_limiter_allows_everything(self, enabled_limiter):
        settings.rate_limit_enabled = False
        request = make_request("10.9.9.2")

        for _ in range(5):
            check_rate_limit(request, "any-scope", 1, 60)

    def test_redis_failure_fails_open(self, enabled_limiter, monkeypatch):
        import app.utils.rate_limit as limiter

        def broken_client():
            raise ConnectionError("redis down")

        monkeypatch.setattr(limiter, "get_redis_client", broken_client)
        check_rate_limit(make_request("10.9.9.3"), "any-scope", 1, 60)
