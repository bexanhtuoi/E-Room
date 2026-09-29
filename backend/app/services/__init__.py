"""Business layer facade.

Submodules hold business logic; *Crud singletons are re-exported here
from app.repositories so existing callers keep working.
New code should import data access from app.repositories directly.
"""
from app.services.base import CRUDRepository
from app.services.document import document_crud
from app.services.message import message_crud
from app.services.notification import notification_crud
from app.services.pronunciation_score import pronunciation_score_crud
from app.services.room import room_crud
from app.services.session import session_crud
from app.services.user import user_crud

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
