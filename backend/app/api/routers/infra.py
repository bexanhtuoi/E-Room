from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.infrastructure.livekit import LiveKitService
from app.infrastructure.minio import get_minio_client
from app.infrastructure.redis_client import RateLimiter, get_redis_client
from app.infrastructure.video import VideoRoomService

router = APIRouter()


@router.get("/status")
async def get_infra_status() -> dict[str, object]:
    redis_client = get_redis_client()
    redis_ok = False
    try:
        redis_ok = bool(redis_client.ping())
    except Exception:
        redis_ok = False

    video_service = VideoRoomService()
    livekit_service = LiveKitService()

    return {
        "redis": redis_ok,
        "minio": {"endpoint": settings.minio_endpoint, "bucket": settings.minio_bucket},
        "celery": {"broker": settings.redis_url},
        "video": video_service.create_room_payload("demo-room", 5),
        "livekit": {"server": livekit_service.server_url, "apiKey": settings.livekit_api_key},
        "websocket": {"path": "/ws/rooms/{room_id}"},
    }


def _check_redis(checks: dict, failures: int) -> int:
    try:
        redis_client = get_redis_client()
        redis_pong = redis_client.ping()
        checks["redis"] = {"status": "ok" if redis_pong else "down", "ping_ms": None}
    except Exception as e:
        checks["redis"] = {"status": "down", "error": str(e)}
        return failures + 1
    return failures


def _check_minio(checks: dict, failures: int) -> int:
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
            "status": "down", "endpoint": settings.minio_endpoint,
            "bucket": settings.minio_bucket, "error": str(e),
        }
        failures += 1
    return failures


def _check_livekit(checks: dict, failures: int) -> int:
    try:
        livekit_service = LiveKitService()
        token = livekit_service.generate_admin_token("health-check-room")
        checks["livekit"] = {
            "status": "ok",
            "server": livekit_service.server_url,
            "token_generated": bool(token),
        }
    except Exception as e:
        checks["livekit"] = {"status": "down", "server": settings.livekit_url, "error": str(e)}
        failures += 1
    return failures


def _overall_status(failures: int) -> tuple[str, int]:
    if failures == 0:
        return "ok", 200
    if failures <= 1:
        return "degraded", 200
    return "down", 503


@router.get("/health")
async def health_check() -> dict[str, object]:
    checks: dict[str, object] = {}
    failures = 0

    failures = _check_redis(checks, failures)
    failures = _check_minio(checks, failures)
    failures = _check_livekit(checks, failures)

    overall, status_code = _overall_status(failures)

    return JSONResponse(
        content={"status": overall, "service": "e-room-api", "checks": checks},
        status_code=status_code,
    )


@router.get("/health/live")
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


async def rate_limit_login(request: Request) -> None:
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
