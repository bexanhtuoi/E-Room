from fastapi import APIRouter

from app.api.routers import auth, document, google_auth, message, notification, room, user

api_router = APIRouter()

api_router.include_router(auth, prefix="/auth", tags=["auth"])
api_router.include_router(google_auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(user, prefix="/users", tags=["users"])
api_router.include_router(room, prefix="/rooms", tags=["rooms"])
api_router.include_router(message, prefix="/messages", tags=["messages"])
api_router.include_router(notification, prefix="/notifications", tags=["notifications"])
api_router.include_router(document, prefix="/documents", tags=["documents"])
