from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.api.dependencies import get_db_session, get_pagination_params
from app.model import Message, Room, RoomParticipant, RoomStatus, Session as RoomSession
from app.schemas import RoomCreateRequest, RoomDetailResponse, RoomJoinRequest, RoomMatchRequest, RoomResponse
from app.service.message import MessageService
from app.service.room import RoomParticipantService, RoomService
from app.service.conversation import SessionService

router = APIRouter()


def _room_to_response(room: Room) -> RoomResponse:
    return RoomResponse(
        id=str(room.id),
        livekit_room_name=room.livekit_room_name,
        topic=room.topic,
        tags=room.tags,
        agent_level=room.agent_level,
        english_level=room.english_level,
        status=room.status,
        max_participants=room.max_participants,
        current_participants=room.current_participants,
        is_public=room.is_public,
    )


@router.get("/", response_model=list[RoomResponse])
async def list_rooms(pagination: tuple[int, int] = Depends(get_pagination_params), session: Session = Depends(get_db_session)) -> list[RoomResponse]:
    room_service = RoomService(session)
    skip, limit = pagination
    rooms = room_service.list_all()[skip : skip + limit]
    return [_room_to_response(room) for room in rooms]


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(payload: RoomCreateRequest, session: Session = Depends(get_db_session)) -> RoomResponse:
    room_service = RoomService(session)
    room = Room(
        livekit_room_name=payload.topic.lower().replace(" ", "-"),
        topic=payload.topic,
        tags=payload.tag_ids,
        max_participants=payload.max_participants,
        is_public=payload.is_public,
        status=RoomStatus.MATCHING,
    )
    saved_room = room_service.save(room)
    return _room_to_response(saved_room)


@router.get("/{room_id}", response_model=RoomDetailResponse)
async def get_room(room_id: UUID, session: Session = Depends(get_db_session)) -> RoomDetailResponse:
    room_service = RoomService(session)
    participant_service = RoomParticipantService(session)
    message_service = MessageService(session)

    room = room_service.get_by_id(room_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    participants = participant_service.list_room_participants(room_id)
    room_messages = message_service.list_room_messages(room_id)

    return RoomDetailResponse(
        id=str(room.id),
        livekit_room_name=room.livekit_room_name,
        topic=room.topic,
        tags=room.tags,
        agent_level=room.agent_level,
        english_level=room.english_level,
        status=room.status,
        max_participants=room.max_participants,
        current_participants=room.current_participants,
        is_public=room.is_public,
        participants=[str(p.user_id) for p in participants],
        messages=[{"id": str(m.id), "content": m.content, "type": m.message_type} for m in room_messages[-20:]],
    )


@router.post("/{room_id}/join", response_model=dict[str, str])
async def join_room(room_id: UUID, payload: RoomJoinRequest, session: Session = Depends(get_db_session)) -> dict[str, str]:
    room_service = RoomService(session)
    participant_service = RoomParticipantService(session)
    session_service = SessionService(session)

    room = room_service.get_by_id(room_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    if room.current_participants >= room.max_participants:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Room is full")

    participant = RoomParticipant(room_id=room_id, user_id=UUID(payload.user_id))
    participant_service.add_participant(participant)

    room.current_participants += 1
    if room.status in {RoomStatus.IDLE, RoomStatus.MATCHING}:
        room.status = RoomStatus.ACTIVE
    room_service.save(room)

    user_session = RoomSession(
        room_id=room_id,
        user_id=UUID(payload.user_id),
        topic=room.topic,
        tags=room.tags,
        speaking_time_seconds=0,
        words_spoken=0,
        duration_seconds=0,
    )
    session_service.save(user_session)

    return {"status": "joined", "roomId": str(room_id), "sessionId": str(user_session.id)}


@router.post("/{room_id}/leave", response_model=dict[str, str])
async def leave_room(room_id: UUID, payload: RoomJoinRequest, session: Session = Depends(get_db_session)) -> dict[str, str]:
    participant_service = RoomParticipantService(session)
    room_service = RoomService(session)

    room = room_service.get_by_id(room_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    room.current_participants = max(0, room.current_participants - 1)
    if room.current_participants == 0:
        room.status = RoomStatus.END
    room_service.save(room)

    return {"status": "left", "roomId": str(room_id)}


@router.post("/match", response_model=dict[str, str])
async def match_room(_: RoomMatchRequest) -> dict[str, str]:
    return {"status": "queued", "message": "Matching request queued"}
