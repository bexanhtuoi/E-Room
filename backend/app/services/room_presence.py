from sqlmodel import Session

from app.ai.tasks import enqueue_room_observer, enqueue_room_transcriber, mark_room_activity
from app.integration.redis import expire, sadd, scard, srem
from app.models import RoomStatus
from app.services import room_crud, session_crud, user_crud
from app.utils.datetime_utils import as_naive_utc, now_utc


def coerce_user_id(participant_identity) -> int | None:
    try:
        return int(str(participant_identity))
    except (TypeError, ValueError):
        return None


def open_room_session(db: Session, room_id: int, user_id: int | None) -> None:
    if user_id is None:
        return
    if not user_crud.get_one(db, id=user_id):
        return
    if session_crud.get_open(db, user_id=user_id, room_id=room_id):
        return
    session_crud.create(db, obj_in={"user_id": user_id, "room_id": room_id})


def close_room_session(db: Session, room_id: int, user_id: int | None) -> None:
    if user_id is None:
        return
    db_session = session_crud.get_open(db, user_id=user_id, room_id=room_id)
    if not db_session:
        return
    left_at = now_utc()
    joined_at = as_naive_utc(db_session.joined_at)
    session_crud.update(
        db,
        db_obj=db_session,
        obj_in={"left_at": left_at, "duration_seconds": max(0, int((as_naive_utc(left_at) - joined_at).total_seconds()))},
    )


def parse_room_id(room_name: str) -> int | None:
    try:
        return int(room_name)
    except (TypeError, ValueError):
        return None


def register_participant_join(db: Session, room_name: str, participant_identity: str) -> None:
    redis_key = f"room:{room_name}:participants"
    sadd(redis_key, str(participant_identity))
    expire(redis_key, 6 * 3600)
    room_id_int = parse_room_id(room_name)
    if room_id_int is None:
        return
    mark_room_activity(room_id_int)
    db_room = room_crud.get_one(db, id=room_id_int)
    if db_room and db_room.status != RoomStatus.ACTIVE:
        room_crud.update(db, db_obj=db_room, obj_in={"status": RoomStatus.ACTIVE})
    open_room_session(db, room_id_int, coerce_user_id(participant_identity))
    enqueue_room_observer(room_id_int)
    enqueue_room_transcriber(room_id_int)


def drop_participant_from_room(db: Session, room_name: str, participant_identity: str) -> None:
    redis_key = f"room:{room_name}:participants"
    srem(redis_key, str(participant_identity))
    if scard(redis_key) > 0:
        return
    room_id_int = parse_room_id(room_name)
    if room_id_int is None:
        return
    db_room = room_crud.get_one(db, id=room_id_int)
    if db_room and db_room.status == RoomStatus.ACTIVE:
        room_crud.update(db, db_obj=db_room, obj_in={"status": RoomStatus.IDLE})
    close_room_session(db, room_id_int, coerce_user_id(participant_identity))
