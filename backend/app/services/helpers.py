import json
from datetime import datetime, timezone
from typing import Optional

from app.shared.constants import SESSION_CHAT_KEY
from app.shared.exceptions import NotAuthenticatedError, NotAuthorizedError

__all__ = [
    "avatar_marker",
    "coerce_user_id",
    "document_scope",
    "ensure_owner",
    "is_session_chat",
    "parse_log_time",
    "parse_room_id",
]


def ensure_owner(owner_id: int, user) -> None:
    if user is None:
        raise NotAuthenticatedError()

    if str(owner_id) == str(user.id):
        return

    if user.role == "admin":
        return

    raise NotAuthorizedError()


def coerce_user_id(participant_identity) -> Optional[int]:
    try:
        return int(str(participant_identity))
    except (TypeError, ValueError):
        return None


def parse_room_id(room_name: str) -> Optional[int]:
    try:
        return int(room_name)
    except (TypeError, ValueError):
        return None


def avatar_marker(user_id: int) -> str:
    return f"avatar:{user_id}"


def document_scope(user) -> dict:
    if user.role == "admin":
        return {}

    return {"user_id": user.id}


def is_session_chat(message) -> bool:
    try:
        return bool((json.loads(message.meta_data or "{}") or {}).get(SESSION_CHAT_KEY))
    except (TypeError, ValueError):
        return False


def parse_log_time(value) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed
