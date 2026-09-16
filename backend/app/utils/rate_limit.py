from fastapi import HTTPException, Request, status

from app.config import settings
from app.integration.redis import get_redis_client
from app.log import get_logger

log = get_logger("app.auth")

RATE_LIMIT_PREFIX = "ratelimit"


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")

    if forwarded:
        return forwarded.split(",")[0].strip()

    if request.client is not None:
        return request.client.host

    return "unknown"


def check_rate_limit(request: Request, scope: str, limit: int, window_seconds: int) -> None:
    if not settings.rate_limit_enabled:
        return

    key = f"{RATE_LIMIT_PREFIX}:{scope}:{client_ip(request)}"

    try:
        client = get_redis_client()
        attempts = client.incr(key)

        if attempts == 1:
            client.expire(key, window_seconds)

        if attempts > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many attempts, please try again later",
            )
    except HTTPException:
        raise
    except Exception as error:
        log.warning("Rate limit skipped | scope=%s error=%s", scope, error)
