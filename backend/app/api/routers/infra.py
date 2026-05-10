from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.infrastructure.redis import get_redis_client
from app.infrastructure.video import VideoRoomService
from app.infrastructure.livekit import LiveKitService
from app.infrastructure.minio import get_minio_client

router = APIRouter()


@router.get("/status")
async def get_infra_status() -> dict[str, object]:
    redis_client = get_redis_client()
    video_service = VideoRoomService()
    livekit_service = LiveKitService()

    redis_ok = False
    try:
        redis_ok = bool(redis_client.ping())
    except Exception:
        redis_ok = False

    return {
        "redis": redis_ok,
        "minio": {
            "endpoint": settings.minio_endpoint,
            "bucket": settings.minio_bucket,
        },
        "celery": {
            "broker": settings.redis_url,
        },
        "video": video_service.create_room_payload("demo-room", 5),
        "livekit": {
            "server": livekit_service.base_url,
            "apiKey": livekit_service.api_key,
        },
        "websocket": {
            "path": "/ws/rooms/{room_id}",
        },
    }


@router.get("/health")
async def health_check() -> dict[str, object]:
    checks: dict[str, object] = {}
    failures = 0

    try:
        redis_client = get_redis_client()
        redis_pong = redis_client.ping()
        checks["redis"] = {"status": "ok" if redis_pong else "down", "ping_ms": None}
    except Exception as e:
        checks["redis"] = {"status": "down", "error": str(e)}
        failures += 1

    try:
        minio_client = get_minio_client()
        bucket_exists = minio_client.bucket_exists(settings.minio_bucket)
        checks["minio"] = {
            "status": "ok" if bucket_exists else "degraded",
            "endpoint": settings.minio_endpoint,
            "bucket": settings.minio_bucket,
            "bucket_exists": bucket_exists,
        }
        if not bucket_exists:
            failures += 1
    except Exception as e:
        checks["minio"] = {
            "status": "down",
            "endpoint": settings.minio_endpoint,
            "bucket": settings.minio_bucket,
            "error": str(e),
        }
        failures += 1

    try:
        livekit_service = LiveKitService()
        token = livekit_service.generate_admin_token("health-check-room")
        checks["livekit"] = {
            "status": "ok",
            "server": livekit_service.server_url,
            "token_generated": bool(token),
        }
    except Exception as e:
        checks["livekit"] = {
            "status": "down",
            "server": settings.livekit_url,
            "error": str(e),
        }
        failures += 1

    overall = "ok" if failures == 0 else ("degraded" if failures <= 1 else "down")
    status_code = 200 if overall == "ok" else (200 if overall == "degraded" else 503)

    return JSONResponse(
        content={
            "status": overall,
            "service": "e-room-api",
            "checks": checks,
        },
        status_code=status_code,
    )


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


async def rate_limit_login(request: Request) -> None:
    from fastapi import HTTPException, status

    from app.infrastructure.redis import RateLimiter

    ip = request.client.host if request.client else "unknown"
    try:
        limiter = RateLimiter()
        allowed, remaining = limiter.check_login(ip)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
                headers={"Retry-After": "900", "X-RateLimit-Remaining": "0"},
            )
    except HTTPException:
        raise
    except Exception:
        pass
