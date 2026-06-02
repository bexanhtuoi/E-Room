from fastapi import APIRouter

from app.api.routers import (
    auth,
    conversation,
    health,
    infra,
    leaderboard,
    message,
    notes,
    notification,
    room,
    series,
    subscription,
    tag,
    user,
)
from app.api.routers.websocket_routes import router as websocket_router  # noqa: F401

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(tag.router, prefix="/tags", tags=["tags"])
api_router.include_router(room.router, prefix="/rooms", tags=["rooms"])
api_router.include_router(conversation.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(message.router, prefix="/messages", tags=["messages"])
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
api_router.include_router(series.router, prefix="/series", tags=["series"])
api_router.include_router(leaderboard.router, prefix="/leaderboard", tags=["leaderboard"])
api_router.include_router(notification.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(infra.router, prefix="/infra", tags=["infra"])
api_router.include_router(subscription.router, prefix="/subscriptions", tags=["subscriptions"])
