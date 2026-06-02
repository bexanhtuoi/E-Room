from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.api.dependencies import get_current_user, get_db_session, get_pagination_params
from app.infrastructure.livekit import LiveKitService
from app.model import Room, RoomParticipant, RoomStatus, Session as RoomSession
from app.schemas import (
    RoomCreateRequest,
    RoomDetailResponse,
    RoomJoinRequest,
    RoomMatchRequest,
    RoomResponse,
    RoomTokenResponse,
)
from app.service.conversation import SessionService
from app.service.message import MessageService
from app.service.room import RoomParticipantService, RoomService

router = APIRouter()
livekit = LiveKitService()

def _room_to_response(room: Room) -> RoomResponse:
    return RoomResponse(
        id=str(room.id),
        livekit_room_name=room.livekit_room_name,
        topic=room.topic,
        tags=room.tags if room.tags else [],
        agent_level=room.agent_level or "basic",
        english_level=room.english_level or "any",
        status=room.status or RoomStatus.MATCHING,
        max_participants=room.max_participants,
        current_participants=room.current_participants,
        is_public=room.is_public,
    )

def _get_room_or_404(room_service: RoomService, room_id: UUID) -> Room:
    room = room_service.get_by_id(room_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room

def _check_room_not_full(room: Room) -> None:
    if room.current_participants >= room.max_participants:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Room is full"
        )

def _add_participant_and_count(
    participant_service: RoomParticipantService,
    room: Room,
    participant: RoomParticipant,
) -> None:
    participant_service.add_participant(participant)
    room.current_participants += 1

@router.get("", response_model=list[RoomResponse])
@router.get("/", response_model=list[RoomResponse])
async def list_rooms(
    pagination: tuple[int, int] = Depends(get_pagination_params),
    session: Session = Depends(get_db_session),
) -> list[RoomResponse]:
    room_service = RoomService(session)
    skip, limit = pagination
    rooms = room_service.list_all()[skip : skip + limit]
    return [_room_to_response(room) for room in rooms]

@router.post("", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    payload: RoomCreateRequest,
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> RoomResponse:
    room_service = RoomService(session)
    safe_name = payload.topic.lower().replace(" ", "-")[:40]
    room = Room(
        livekit_room_name=f"{safe_name}-{uuid4().hex[:8]}",
        topic=payload.topic,
        tags=payload.tag_ids,
        max_participants=payload.max_participants,
        is_public=payload.is_public,
        status=RoomStatus.MATCHING,
    )
    saved_room = room_service.save(room)

    _add_participant_and_count(
        RoomParticipantService(session),
        saved_room,
        RoomParticipant(room_id=saved_room.id, user_id=UUID(current_user["id"])),
    )
    room_service.save(saved_room)

    return _room_to_response(saved_room)

@router.get("/{room_id}", response_model=RoomDetailResponse)
async def get_room(
    room_id: UUID, session: Session = Depends(get_db_session)
) -> RoomDetailResponse:
    room_service = RoomService(session)
    room = _get_room_or_404(room_service, room_id)

    participant_service = RoomParticipantService(session)
    message_service = MessageService(session)

    participants = participant_service.list_room_participants(room_id)
    room_messages = message_service.list_room_messages(room_id)

    return RoomDetailResponse(
        id=str(room.id),
        livekit_room_name=room.livekit_room_name,
        topic=room.topic,
        tags=room.tags if room.tags else [],
        agent_level=room.agent_level or "basic",
        english_level=room.english_level or "any",
        status=room.status,
        max_participants=room.max_participants,
        current_participants=room.current_participants,
        is_public=room.is_public,
        participants=[str(p.user_id) for p in participants],
        messages=[
            {"id": str(m.id), "content": m.content, "type": m.message_type}
            for m in room_messages[-20:]
        ],
    )

@router.post("/{room_id}/join", response_model=dict)
async def join_room(
    room_id: UUID,
    payload: RoomJoinRequest,
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    user_id = UUID(current_user["id"])
    room_service = RoomService(session)
    participant_service = RoomParticipantService(session)
    session_service = SessionService(session)

    room = _get_room_or_404(room_service, room_id)
    _check_room_not_full(room)

    existing = participant_service.get_room_participant(room_id, user_id)
    if existing is None:
        _add_participant_and_count(
            participant_service, room,
            RoomParticipant(room_id=room_id, user_id=user_id),
        )

    if room.status in {RoomStatus.IDLE, RoomStatus.MATCHING}:
        room.status = RoomStatus.ACTIVE
    room_service.save(room)

    existing_session = session_service.get_room_user_session(room_id, user_id)
    if existing_session is None:
        user_session = RoomSession(
            room_id=room_id,
            user_id=user_id,
            topic=room.topic,
            tags=room.tags,
            speaking_time_seconds=0,
            words_spoken=0,
            duration_seconds=0,
        )
        session_service.save(user_session)
    else:
        user_session = existing_session

    return {"status": "joined", "roomId": str(room_id), "sessionId": str(user_session.id)}

@router.post("/{room_id}/leave", response_model=dict)
async def leave_room(
    room_id: UUID,
    payload: RoomJoinRequest,
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    user_id = UUID(current_user["id"])
    room_service = RoomService(session)
    participant_service = RoomParticipantService(session)
    room = _get_room_or_404(room_service, room_id)

    participant = participant_service.get_room_participant(room_id, user_id)
    if participant:
        participant_service.session.delete(participant)
        participant_service.session.commit()
        room.current_participants = max(0, room.current_participants - 1)

    if room.current_participants == 0:
        room.status = RoomStatus.END
    room_service.save(room)

    return {"status": "left", "roomId": str(room_id)}

@router.post("/{room_id}/token", response_model=RoomTokenResponse)
async def get_room_token(
    room_id: UUID,
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> RoomTokenResponse:
    room_service = RoomService(session)
    room = _get_room_or_404(room_service, room_id)

    token = livekit.generate_token(
        room_name=room.livekit_room_name,
        participant_identity=str(current_user["id"]),
        participant_name=current_user.get("display_name", current_user.get("email", "")),
    )

    return RoomTokenResponse(
        room_id=str(room_id),
        room_name=room.livekit_room_name,
        livekit_token=token,
        livekit_url=livekit.server_url,
    )

@router.post("/match", response_model=dict)
async def match_room(
    payload: RoomMatchRequest,
    session: Session = Depends(get_db_session),
    current_user: dict = Depends(get_current_user),
) -> dict:
    _ = current_user  # auth check
    room_service = RoomService(session)
    rooms = room_service.list_all()
    open_rooms = [r for r in rooms if r.status in {RoomStatus.MATCHING, RoomStatus.IDLE}]
    if payload.tag_ids:
        matching = [r for r in open_rooms if any(tag in (r.tags or []) for tag in payload.tag_ids)]
    else:
        matching = open_rooms
    if not matching and open_rooms:
        matching = open_rooms[:1]
    if matching:
        best = matching[0]
        return {"status": "matched", "roomId": str(best.id), "roomName": best.livekit_room_name}
    return {"status": "queued", "message": "No rooms available right now"}
