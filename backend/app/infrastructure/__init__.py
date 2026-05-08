"""Infrastructure layer — external service clients and reusable CRUD utilities.

All clients are obtained via their factory/getter functions (never
instantiated directly), so they are trivial to mock in tests and safe
to import anywhere.
"""

from app.infrastructure.celery_app import celery_app
from app.infrastructure.crud import MinioCRUD, RedisCRUD
from app.infrastructure.livekit_service import LiveKitService
from app.infrastructure.minio_client import get_minio_client
from app.infrastructure.redis_client import get_redis_client
from app.infrastructure.room_state import RoomStateRepository
from app.infrastructure.video import VideoRoomService
from app.infrastructure.websocket import websocket_manager

__all__ = [
    # celery
    "celery_app",
    # crud (reusable)
    "MinioCRUD",
    "RedisCRUD",
    # clients
    "get_minio_client",
    "get_redis_client",
    # services
    "LiveKitService",
    "RoomStateRepository",
    "VideoRoomService",
    "websocket_manager",
]
