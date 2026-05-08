from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.infrastructure.redis import get_redis_client
from app.infrastructure.video import VideoRoomService
from app.infrastructure.livekit import LiveKitService

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
