from app.repositories.base import CRUDRepository
from app.repositories.document import document_crud
from app.repositories.message import message_crud
from app.repositories.notification import notification_crud
from app.repositories.pronunciation_score import pronunciation_score_crud
from app.repositories.room import room_crud
from app.repositories.session import session_crud
from app.repositories.user import user_crud

__all__ = [
    "CRUDRepository",
    "document_crud",
    "message_crud",
    "notification_crud",
    "pronunciation_score_crud",
    "room_crud",
    "session_crud",
    "user_crud",
]
