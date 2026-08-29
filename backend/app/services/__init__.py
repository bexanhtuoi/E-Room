from app.services.base import CRUDRepository
from app.services.document import document_crud
from app.services.message import message_crud
from app.services.notification import notification_crud
from app.services.room import room_crud
from app.services.user import user_crud

__all__ = [
    "CRUDRepository",
    "document_crud",
    "message_crud",
    "notification_crud",
    "room_crud",
    "user_crud",
]
