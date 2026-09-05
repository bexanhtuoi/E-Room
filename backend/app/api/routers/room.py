from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.ai.tasks import enqueue_room_observer, enqueue_room_transcriber, mark_room_activity
from app.api.dependencies import authorize_owner, get_pagination_params, require_auth
from app.config import settings
from app.database import get_session
from app.integration.livekit import create_token, verify_webhook
from app.integration.redis import delete as redis_delete
from app.integration.redis import sadd, scard, smembers, srem
from app.models import RoomStatus
from app.schemas import (
    RoomCreateSchema,
    RoomMatchRequest,
    RoomMatchResponse,
    RoomResponse,
    RoomTokenResponse,
    RoomUpdateSchema,
)
from app.schemas.room import topics_to_json
from app.services import message_crud, room_crud

router = APIRouter()


@router.get("/", response_model=List[RoomResponse])
def get_rooms(
    db: Session = Depends(get_session),
    pagination: tuple[int, int] = Depends(get_pagination_params),
) -> List[RoomResponse]:
    skip, limit = pagination
    rooms = room_crud.get_many(db, skip=skip, limit=limit, order_by="id", desc=True)
    return rooms


@router.get("/count")
def count_rooms(db: Session = Depends(get_session)) -> dict:
    return {"count": room_crud.count(db)}


@router.get("/{room_id}", response_model=RoomResponse)
def get_room(room_id: int, db: Session = Depends(get_session)) -> RoomResponse:
    db_room = room_crud.get_one(db, id=room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return db_room


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
def create_room(
    room_in: RoomCreateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomResponse:
    db_room = room_crud.get_one(db, name=room_in.name)
    if db_room:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room name already exists")

    obj_in_data = room_in.model_dump()
    obj_in_data["host_id"] = request.state.current_user.id
    obj_in_data["topics"] = topics_to_json(obj_in_data.get("topics"))
    new_room = room_crud.create(db, obj_in=obj_in_data)

    return new_room


@router.post("/match", response_model=RoomMatchResponse)
def match_room(
    match_in: RoomMatchRequest,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomMatchResponse:
    candidates = [room for room in room_crud.get_many(db, limit=200) if room.status != RoomStatus.ENDED]

    topic_query = (match_in.topic or "").strip().lower()
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No open rooms right now. Try creating one!")

    priority = {RoomStatus.ACTIVE: 0, RoomStatus.IDLE: 1}
    best = sorted(candidates, key=lambda room: (priority.get(room.status, 3), room.id or 0))[0]
    return RoomMatchResponse(status="matched", room=best)


@router.patch("/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: int,
    room_in: RoomUpdateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomResponse:
    db_room = room_crud.get_one(db, id=room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    authorize_owner(db_room.host_id, request)

    obj_in_data = room_in.model_dump(exclude_unset=True)
    if "topics" in obj_in_data:
        obj_in_data["topics"] = topics_to_json(obj_in_data.get("topics"))
    updated_room = room_crud.update(db, db_obj=db_room, obj_in=obj_in_data)
    return updated_room


def delete_related_data(db: Session, room_id: int) -> None:
    # Xoa toan bo messages cua room truoc khi xoa room
    for message in message_crud.get_many(db, room_id=room_id):
        message_crud.delete(db, db_obj=message)

    # Xoa danh sach participants trong Redis
    redis_delete(f"room:{room_id}:participants")


@router.delete("/{room_id}", response_model=RoomResponse)
def delete_room(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomResponse:
    db_room = room_crud.get_one(db, id=room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    authorize_owner(db_room.host_id, request)

    delete_related_data(db, room_id)
    deleted_room = room_crud.delete(db, db_obj=db_room)
    return deleted_room


@router.post("/{room_id}/token", response_model=RoomTokenResponse)
def get_room_token(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> RoomTokenResponse:
    db_room = room_crud.get_one(db, id=room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    current_user = request.state.current_user
    token = create_token(
        room_name=str(db_room.id),
        user_id=current_user.id,
        user_name=current_user.full_name,
    )

    return RoomTokenResponse(
        livekit_token=token,
        livekit_url=settings.livekit_url,
        room_name=str(db_room.id),
    )


@router.get("/{room_id}/participants")
def get_room_participants(
    room_id: int,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    db_room = room_crud.get_one(db, id=room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    participants = list(smembers(f"room:{room_id}:participants"))

    return {
        "room_id": room_id,
        "count": len(participants),
        "participants": participants,
    }


@router.post("/livekit/webhook")
async def handle_livekit_webhook(
    request: Request,
    db: Session = Depends(get_session),
) -> dict:
    auth_header = request.headers.get("Authorization", "")
    event = verify_webhook(auth_header)
    if not event:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook token")

    body = await request.json()
    event_type = body.get("event") or event.get("event")
    room_name = body.get("room", {}).get("name") or event.get("room", {}).get("name")
    participant_identity = body.get("participant", {}).get("identity") or event.get("participant", {}).get("identity")

    if not room_name:
        return {"status": "ignored"}
    if participant_identity and participant_identity.startswith("ai_"):
        return {"status": "ignored"}

    redis_key = f"room:{room_name}:participants"

    if event_type == "participant_joined" and participant_identity:
        try:
            register_participant_join(db, room_name, participant_identity)
        except ValueError:
            pass

    elif event_type == "participant_left" and participant_identity:
        drop_participant_from_room(db, room_name, participant_identity)

    return {"status": "success", "event": event_type}


def register_participant_join(db: Session, room_name: str, participant_identity: str) -> None:
    redis_key = f"room:{room_name}:participants"
    sadd(redis_key, str(participant_identity))
    room_id_int = int(room_name)
    mark_room_activity(room_id_int)
    db_room = room_crud.get_one(db, id=room_id_int)
    if db_room and db_room.status != RoomStatus.ACTIVE:
        room_crud.update(db, db_obj=db_room, obj_in={"status": RoomStatus.ACTIVE})
    enqueue_room_observer(room_id_int)
    enqueue_room_transcriber(room_id_int)


@router.post("/{room_id}/join")
def join_room(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    # Client goi truc tiep khi LiveKit onConnected — khong phu thuoc webhook
    # (webhook Cloud co the chua cau hinh / miss). Idempotent.
    db_room = room_crud.get_one(db, id=room_id)
    if not db_room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    register_participant_join(db, str(room_id), request.state.current_user.id)
    return {"status": "joined", "room_id": room_id}


def drop_participant_from_room(db: Session, room_name: str, participant_identity: str) -> None:
    redis_key = f"room:{room_name}:participants"
    srem(redis_key, str(participant_identity))
    if scard(redis_key) > 0:
        return
    try:
        room_id_int = int(room_name)
    except ValueError:
        return
    db_room = room_crud.get_one(db, id=room_id_int)
    # Phong het nguoi → IDLE (van hien trong list de vao lai),
    # chi ENDED khi bo hoang lau (heartbeat xu ly).
    if db_room and db_room.status == RoomStatus.ACTIVE:
        room_crud.update(db, db_obj=db_room, obj_in={"status": RoomStatus.IDLE})


@router.post("/{room_id}/leave")
def leave_room(
    room_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    # Client goi truc tiep khi bam Leave/back — khong doi webhook LiveKit
    # (webhook co the miss khi tab dong dot ngot hoac server restart).
    drop_participant_from_room(db, str(room_id), request.state.current_user.id)
    return {"status": "left", "room_id": room_id}
