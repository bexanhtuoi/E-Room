from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_pagination_params
from app.model import Room, RoomStatus
from app.schemas import RoomCreateRequest, RoomMatchRequest, RoomResponse
from app.service.room import RoomService

router = APIRouter()
room_service = RoomService()


@router.get("/", response_model=list[RoomResponse])
async def list_rooms(pagination: tuple[int, int] = Depends(get_pagination_params)) -> list[RoomResponse]:
    skip, limit = pagination
    rooms = room_service.list_all()[skip : skip + limit]
    return [
        RoomResponse(
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
        for room in rooms
    ]


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(payload: RoomCreateRequest) -> RoomResponse:
    room = Room(livekit_room_name=payload.topic.lower().replace(" ", "-"), topic=payload.topic, tags=payload.tag_ids, max_participants=payload.max_participants, is_public=payload.is_public)
    room.status = RoomStatus.MATCHING
    saved_room = room_service.save(room)
    return RoomResponse(
        id=str(saved_room.id),
        livekit_room_name=saved_room.livekit_room_name,
        topic=saved_room.topic,
        tags=saved_room.tags,
        agent_level=saved_room.agent_level,
        english_level=saved_room.english_level,
        status=saved_room.status,
        max_participants=saved_room.max_participants,
        current_participants=saved_room.current_participants,
        is_public=saved_room.is_public,
    )


@router.post("/match", response_model=dict[str, str])
async def match_room(_: RoomMatchRequest) -> dict[str, str]:
    return {"status": "queued", "message": "Matching request accepted"}
