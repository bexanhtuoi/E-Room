from fastapi import APIRouter

from app.api.routers import auth, conversation, health, message, room, tag, user

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(user.router, prefix="/users", tags=["users"])
api_router.include_router(tag.router, prefix="/tags", tags=["tags"])
api_router.include_router(room.router, prefix="/rooms", tags=["rooms"])
api_router.include_router(conversation.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(message.router, prefix="/messages", tags=["messages"])
