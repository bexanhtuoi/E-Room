from typing import Optional

from sqlmodel import Session

from app.log import get_logger
from app.models import MessageRole
from app.repositories.message import MessageCrud, is_recent_duplicate, message_crud
from app.repositories.room import room_crud
from app.services.helpers import ensure_owner
from app.services.session import is_session_chat
from app.shared.exceptions import (
    BadRequestError,
    MessageNotFoundError,
    NotAuthorizedError,
    RoomNotFoundError,
)
from app.utils.chat import scrub_meta, strip_ai_mention

log = get_logger("app.services.message")

__all__ = [
    "MessageCrud",
    "create_message",
    "count_messages",
    "delete_message",
    "get_message_data",
    "is_recent_duplicate",
    "list_messages",
    "message_crud",
]


def list_messages(
    db: Session,
    user,
    room_id: Optional[int] = None,
    user_id: Optional[int] = None,
    role: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
) -> list:
    from app.services.room import ensure_room_access

    if room_id is not None:
        room = room_crud.get_one(db, id=room_id)

        if room is not None:
            ensure_room_access(room, user)

    is_self_lookup = user_id is not None and str(user_id) == str(user.id)

    if user_id is not None and room_id is None:
        if not is_self_lookup and user.role != "admin":
            raise NotAuthorizedError()

    if room_id is None and not is_self_lookup and user.role != "admin":
        raise BadRequestError(detail="C?n truy?n room_id.")

    filter_kwargs = {}

    if room_id is not None:
        filter_kwargs["room_id"] = room_id

    if user_id is not None:
        filter_kwargs["user_id"] = user_id

    if role is not None:
        filter_kwargs["role"] = role

    messages = message_crud.get_many(db, skip=skip, limit=limit, order_by="id", desc=True, **filter_kwargs)

    return [message for message in messages if not is_session_chat(message)]


def count_messages(
    db: Session,
    user,
    room_id: Optional[int] = None,
    user_id: Optional[int] = None,
    role: Optional[str] = None,
) -> int:
    from app.services.room import ensure_room_access

    if room_id is not None:
        room = room_crud.get_one(db, id=room_id)

        if room is not None:
            ensure_room_access(room, user)

    if room_id is None and user_id is None and user.role != "admin":
        raise BadRequestError(detail="C?n truy?n room_id ho?c user_id.")

    if user_id is not None and room_id is None:
        if str(user_id) != str(user.id) and user.role != "admin":
            raise NotAuthorizedError()

    filter_kwargs = {}

    if room_id is not None:
        filter_kwargs["room_id"] = room_id

    if user_id is not None:
        filter_kwargs["user_id"] = user_id

    if role is not None:
        filter_kwargs["role"] = role

    return message_crud.count(db, **filter_kwargs)


def get_message_data(db: Session, user, message_id: int):
    from app.services.room import ensure_room_access

    message = message_crud.get_one(db, id=message_id)

    if not message:
        raise MessageNotFoundError()

    room = room_crud.get_one(db, id=message.room_id)

    if room is not None:
        ensure_room_access(room, user)

    return message


def create_message(db: Session, user, message_in):
    from app.services.room import ensure_room_access
    from app.tasks.helpers import mark_room_activity
    from app.tasks.room_jobs import enqueue_ai_job

    room = room_crud.get_one(db, id=message_in.room_id)

    if not room:
        raise RoomNotFoundError()

    ensure_room_access(room, user)

    obj_in_data = message_in.model_dump()
    obj_in_data["user_id"] = user.id
    obj_in_data["role"] = MessageRole.USER
    obj_in_data["meta_data"] = scrub_meta(obj_in_data.get("meta_data"))

    new_message = message_crud.create(db, obj_in=obj_in_data)

    try:
        mark_room_activity(message_in.room_id)
        query = strip_ai_mention(message_in.text)

        if query:
            enqueue_ai_job(
                message_in.room_id,
                "answer",
                query,
                new_message.id,
            )
    except Exception as error:
        log.warning("Message post-processing skipped | room_id=%s error=%s", message_in.room_id, error)

    return new_message


def delete_message(db: Session, user, message_id: int):
    message = message_crud.get_one(db, id=message_id)

    if not message:
        raise MessageNotFoundError()

    ensure_owner(message.user_id, user)

    return message_crud.delete(db, db_obj=message)
