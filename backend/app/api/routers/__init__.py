from app.api.routers.auth import router as auth
from app.api.routers.document import router as document
from app.api.routers.message import router as message
from app.api.routers.notification import router as notification
from app.api.routers.room import router as room
from app.api.routers.user import router as user

__all__ = [
    "auth",
    "document",
    "message",
    "notification",
    "room",
    "user",
]
