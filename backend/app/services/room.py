from typing import Any, Dict, List, Optional
from urllib.parse import quote

from fastapi import UploadFile
from redis.exceptions import RedisError
from sqlmodel import Session

from app.config import settings
from app.integration.livekit import create_token
from app.integration.redis import claim_seat, expire, sadd, scard, smembers, srem
from app.log import get_logger
from app.models import DocumentKind, Notification, NotificationType, Room, RoomStatus, User
from app.repositories.document import document_crud, drop_doc_storage
from app.repositories.notification import notification_crud
from app.repositories.room import RoomCrud, room_crud
from app.repositories.session import session_crud
from app.repositories.user import user_crud
from app.schemas.room import emails_from_json, emails_to_json, topics_to_json
from app.services.helpers import ensure_owner
from app.shared.exceptions import (
    AppException,
    DocumentNotFoundError,
    ExternalServiceError,
    NoOpenRoomsError,
    NotAuthenticatedError,
    NotAuthorizedError,
    PresenceUnavailableError,
    RoomFullError,
    RoomNameExistsError,
    RoomNotFoundError,
    WebhookAuthError,
)
from app.shared.keys import room_presence_key, room_tag
from app.utils.upload import media_type_for, read_upload

log = get_logger("app.services.room")

PRESENCE_TTL_SECONDS = 6 * 3600
MAX_ROOM_FILE_BYTES = 10 * 1024 * 1024
ROOM_FILE_TYPES = {"pdf", "md", "txt"}

__all__ = [
    "MAX_ROOM_FILE_BYTES",
    "PRESENCE_TTL_SECONDS",
    "ROOM_FILE_TYPES",
    "RoomCrud",
    "claim_room_seat",
    "coerce_user_id",
    "count_rooms",
    "create_room",
    "delete_room",
    "delete_room_document",
    "download_room_document",
    "drop_participant_from_room",
    "filter_visible_rooms",
    "get_default_prompt",
    "get_host_room",
    "get_participants_data",
    "get_room_documents",
    "get_room_or_404",
    "get_room_token_data",
    "handle_participant_event",
    "join_room",
    "leave_room",
    "list_rooms",
    "match_room",
    "notify_room_invites",
    "parse_room_id",
    "presence_add",
    "presence_count",
    "presence_members",
    "presence_remove",
    "register_participant_join",
    "room_crud",
    "room_is_full",
    "update_room",
    "upload_room_document",
    "verify_webhook_token",
]


def presence_members(room_id: int) -> set:
    try:
        return set(smembers(room_presence_key(room_id)))
    except RedisError as error:
        log.warning("Presence read failed | room_id=%s error=%s", room_id, error)
        return set()


def presence_count(room_id: int) -> Optional[int]:
    try:
        return scard(room_presence_key(room_id))
    except RedisError as error:
        log.warning("Presence count failed | room_id=%s error=%s", room_id, error)
        return None


def presence_add(room_id: int, identity: str) -> None:
    try:
        key = room_presence_key(room_id)
        sadd(key, str(identity))
        expire(key, PRESENCE_TTL_SECONDS)
    except RedisError as error:
        log.warning("Presence add failed | room_id=%s error=%s", room_id, error)


def presence_remove(room_id: int, identity: str) -> Optional[int]:
    try:
        key = room_presence_key(room_id)
        srem(key, str(identity))
        return scard(key)
    except RedisError as error:
        log.warning("Presence remove failed | room_id=%s error=%s", room_id, error)
        return None


def room_is_full(room: Room, user_id: int) -> bool:
    count = presence_count(room.id)

    if count is None:
        return False

    if str(user_id) in presence_members(room.id):
        return False

    return count >= (room.max_participants or 4)


def claim_room_seat(room: Room, identity: str) -> bool:
    try:
        return claim_seat(room_presence_key(room.id), str(identity), room.max_participants or 4, PRESENCE_TTL_SECONDS)
    except RedisError as error:
        log.warning("Seat claim skipped | room_id=%s error=%s", room.id, error)
        return True


def ensure_room_access(room: Room, user) -> None:
    if not room.is_private:
        return

    if user is None:
        raise NotAuthenticatedError()

    if str(room.host_id) == str(user.id):
        return

    if user.role == "admin":
        return

    allowed = emails_from_json(room.allowed_emails)

    if user.email and user.email.strip().lower() in allowed:
        return

    raise NotAuthorizedError(detail="Phòng này là riêng tư.")


def get_room_or_404(db: Session, room_id: int) -> Room:
    room = room_crud.get_one(db, id=room_id)

    if room is None:
        raise RoomNotFoundError()

    return room


def get_host_room(db: Session, room_id: int, user) -> Room:
    room = get_room_or_404(db, room_id)
    ensure_owner(room.host_id, user)

    return room


def filter_visible_rooms(rooms: List[Room], user) -> List[Room]:
    if user is None:
        return [room for room in rooms if not room.is_private]

    result = []
    for room in rooms:
        try:
            ensure_room_access(room, user)
        except AppException:
            continue
        result.append(room)

    return result


def list_rooms(db: Session, user, skip: int = 0, limit: int = 10, public_only: bool = False) -> List[Room]:
    rooms = room_crud.get_many(db, skip=skip, limit=limit, order_by="id", desc=True)

    if public_only:
        return [room for room in rooms if not room.is_private]

    return filter_visible_rooms(rooms, user)


def count_rooms(db: Session) -> int:
    return room_crud.count(db)


def create_room(db: Session, user, room_in) -> Room:
    if room_crud.get_one(db, name=room_in.name):
        raise RoomNameExistsError()

    obj_in_data = room_in.model_dump()
    obj_in_data["host_id"] = user.id
    obj_in_data["topics"] = topics_to_json(obj_in_data.get("topics"))
    obj_in_data["allowed_emails"] = emails_to_json(obj_in_data.get("allowed_emails"))

    new_room = room_crud.create(db, obj_in=obj_in_data)
    notify_room_invites(db, new_room, emails_from_json(new_room.allowed_emails))

    return new_room


def notify_room_invites(db: Session, room, emails: list) -> int:
    host_name = ""

    if room.host_id:
        host = user_crud.get_one(db, id=room.host_id)
        host_name = (host.full_name if host else "") or ""

    emails = [email for email in emails or []]

    if not emails:
        return 0

    invited_map = {user.email: user for user in user_crud.get_many(db, User.email.in_(emails))}
    invited_ids = [user.id for user in invited_map.values() if user.id != room.host_id]

    sent_ids = set()

    if invited_ids:
        for notif in notification_crud.get_many(db, Notification.user_id.in_(invited_ids)):
            if notif.notification_type == NotificationType.INVITE and room_tag(room.id) in (notif.body or ""):
                sent_ids.add(notif.user_id)

    sent = 0
    for email in emails:
        invited = invited_map.get(email)

        if not invited or invited.id == room.host_id or invited.id in sent_ids:
            continue

        notification_crud.create(
            db,
            obj_in={
                "user_id": invited.id,
                "title": f"You're invited to '{room.name}'",
                "body": f"{host_name + ' invited you to ' if host_name else 'You are invited to '}{room_tag(room.id)}. Open Schedule to join on time.",
                "notification_type": NotificationType.INVITE,
            },
        )
        sent_ids.add(invited.id)
        sent += 1

    return sent


def match_room(db: Session, topic: str = ""):
    candidates = [
        room
        for room in room_crud.get_many(db, limit=200)
        if room.status != RoomStatus.ENDED and not room.is_private
    ]

    topic_query = (topic or "").strip().lower()

    if topic_query:
        scored = []
        for room in candidates:
            haystack = " ".join(
                [
                    room.name or "",
                    room.description or "",
                    room.topics or "",
                ]
            ).lower()
            if topic_query in haystack:
                scored.append(room)
        candidates = scored

    if not candidates:
        raise NoOpenRoomsError()

    priority = {RoomStatus.ACTIVE: 0, RoomStatus.IDLE: 1}

    return sorted(candidates, key=lambda room: (priority.get(room.status, 3), room.id or 0))[0]


def update_room(db: Session, user, room_id: int, room_in) -> Room:
    room = get_room_or_404(db, room_id)
    ensure_owner(room.host_id, user)

    obj_in_data = room_in.model_dump(exclude_unset=True)

    if "topics" in obj_in_data:
        obj_in_data["topics"] = topics_to_json(obj_in_data.get("topics"))

    if "allowed_emails" in obj_in_data:
        obj_in_data["allowed_emails"] = emails_to_json(obj_in_data.get("allowed_emails"))

    updated_room = room_crud.update(db, db_obj=room, obj_in=obj_in_data)

    if "allowed_emails" in obj_in_data:
        notify_room_invites(db, updated_room, emails_from_json(updated_room.allowed_emails))

    return updated_room


def delete_room(db: Session, user, room_id: int) -> Room:
    room = get_room_or_404(db, room_id)
    ensure_owner(room.host_id, user)

    room_crud.delete_cascade(db, room_id)

    return room


def get_default_prompt() -> dict:
    from app.ai.llm.prompt import get_main_prompt

    return {"default_system_prompt": get_main_prompt()}


def get_room_documents(db: Session, user, room_id: int):
    room = get_host_room(db, room_id, user)

    return document_crud.get_many(db, room_id=room.id, order_by="id", desc=True)


async def upload_room_document(db: Session, user, room_id: int, file: UploadFile):
    from app.ai.rag.vector_store import process_document
    from app.integration.minio import delete_object, put_document

    room = get_host_room(db, room_id, user)

    raw, suffix = await read_upload(file, ROOM_FILE_TYPES, MAX_ROOM_FILE_BYTES, "File")
    object_name = put_document(raw, file.filename or f"room-{room_id}.{suffix}")

    new_doc = document_crud.create(
        db,
        obj_in={
            "user_id": user.id,
            "room_id": room.id,
            "kind": DocumentKind.FILE,
            "file_name": file.filename,
            "file_type": suffix,
            "file_path": object_name,
            "metadata_json": f'{{"size": {len(raw)}}}',
        },
    )

    try:
        await process_document(raw, file.filename or object_name, room_tag(room.id), new_doc.id)
    except Exception as error:
        document_crud.delete(db, db_obj=new_doc)

        try:
            delete_object(object_name)
        except Exception:
            pass

        raise ExternalServiceError(detail=f"Không thể index tài liệu: {error}")

    return new_doc


def download_room_document(db: Session, user, room_id: int, document_id: int) -> Dict[str, Any]:
    from app.integration.minio import get_object

    room = get_host_room(db, room_id, user)

    doc = document_crud.get_one(db, id=document_id, room_id=room.id)

    if not doc or doc.kind != DocumentKind.FILE or not doc.file_path:
        raise DocumentNotFoundError(detail="Không tìm thấy file.")

    try:
        data = get_object(doc.file_path)
    except Exception:
        raise DocumentNotFoundError(detail="Không tìm thấy file trong kho lưu trữ.")

    safe_name = (doc.file_name or "file").replace('"', "")

    return {
        "data": data,
        "media_type": media_type_for(doc.file_type),
        "filename": f"inline; filename*=UTF-8''{quote(safe_name)}",
    }


def delete_room_document(db: Session, user, room_id: int, document_id: int):
    room = get_host_room(db, room_id, user)

    doc = document_crud.get_one(db, id=document_id, room_id=room.id)

    if not doc:
        raise DocumentNotFoundError()

    document_crud.delete(db, db_obj=doc)
    drop_doc_storage(doc)

    return doc


def get_room_token_data(db: Session, user, room_id: int) -> Dict[str, Any]:
    room = get_room_or_404(db, room_id)
    ensure_room_access(room, user)

    if room_is_full(room, user.id):
        raise RoomFullError()

    token = create_token(
        room_name=str(room.id),
        user_id=user.id,
        user_name=user.full_name,
    )

    return {
        "livekit_token": token,
        "livekit_url": settings.livekit_url,
        "room_name": str(room.id),
    }


def get_participants_data(db: Session, user, room_id: int) -> Dict[str, Any]:
    room = get_room_or_404(db, room_id)
    ensure_room_access(room, user)

    return _participants_or_raise(room_id)


def _participants_or_raise(room_id: int) -> Dict[str, Any]:
    try:
        participants = list(smembers(room_presence_key(room_id)))
    except RedisError:
        raise PresenceUnavailableError()

    return {
        "room_id": room_id,
        "count": len(participants),
        "participants": participants,
    }


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


def register_participant_join(db: Session, room_name: str, participant_identity: str, enforce_limit: bool = False) -> bool:
    from app.tasks.helpers import mark_room_activity
    from app.tasks.room_jobs import enqueue_room_observer, enqueue_room_transcriber

    room_id_int = parse_room_id(room_name)

    if room_id_int is None:
        return False

    db_room = room_crud.get_one(db, id=room_id_int)

    if db_room is None:
        presence_add(room_id_int, participant_identity)
        return True

    if enforce_limit and not claim_room_seat(db_room, participant_identity):
        return False

    presence_add(room_id_int, participant_identity)
    mark_room_activity(room_id_int)

    if db_room.status != RoomStatus.ACTIVE:
        room_crud.update(db, db_obj=db_room, obj_in={"status": RoomStatus.ACTIVE})

    session_crud.open(db, room_id_int, coerce_user_id(participant_identity))

    try:
        enqueue_room_observer(room_id_int)
        enqueue_room_transcriber(room_id_int)
    except Exception as error:
        log.warning("Room workers not enqueued | room_id=%s error=%s", room_id_int, error)

    return True


def drop_participant_from_room(db: Session, room_name: str, participant_identity: str) -> None:
    from app.tasks.scoring import score_room_utterances

    room_id_int = parse_room_id(room_name)

    if room_id_int is None:
        return

    remaining = presence_remove(room_id_int, participant_identity)

    if remaining is None:
        session_crud.close(db, room_id_int, coerce_user_id(participant_identity))
        return

    if remaining > 0:
        return

    db_room = room_crud.get_one(db, id=room_id_int)

    if db_room and db_room.status == RoomStatus.ACTIVE:
        room_crud.update(db, db_obj=db_room, obj_in={"status": RoomStatus.IDLE})

    session_crud.close(db, room_id_int, coerce_user_id(participant_identity))

    try:
        score_room_utterances.apply_async(args=[room_id_int], queue=settings.ai_queue_name)
    except Exception as error:
        log.warning("Room scoring not enqueued | room_id=%s error=%s", room_id_int, error)


def verify_webhook_token(auth_header: str, raw_body: bytes):
    from app.integration.livekit import verify_webhook

    event = verify_webhook(auth_header, raw_body)

    if not event:
        raise WebhookAuthError()

    return event


def handle_participant_event(db: Session, event_type: str, room_name: str, participant_identity: str) -> None:
    if event_type == "participant_joined" and participant_identity:
        try:
            register_participant_join(db, room_name, participant_identity)
        except ValueError:
            pass

    elif event_type == "participant_left" and participant_identity:
        drop_participant_from_room(db, room_name, participant_identity)


def join_room(db: Session, user, room_id: int) -> Dict[str, Any]:
    room = get_room_or_404(db, room_id)
    ensure_room_access(room, user)

    # Client gọi trực tiếp khi LiveKit onConnected — không phụ thuộc webhook
    # (webhook Cloud có thể chưa cấu hình / miss). Idempotent.
    seated = register_participant_join(db, str(room_id), user.id, enforce_limit=True)

    if not seated:
        raise RoomFullError()

    return {"status": "joined", "room_id": room_id}


def leave_room(db: Session, user, room_id: int) -> Dict[str, Any]:
    # Client gọi trực tiếp khi bấm Leave/back — không đợi webhook LiveKit
    # (webhook có thể miss khi tab đóng đột ngột hoặc server restart).
    drop_participant_from_room(db, str(room_id), user.id)

    return {"status": "left", "room_id": room_id}
