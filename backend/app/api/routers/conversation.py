from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.dependencies import get_db_session, get_pagination_params
from app.schemas import SessionResponse
from app.service.conversation import SessionService

router = APIRouter()


@router.get("/", response_model=list[SessionResponse])
async def list_sessions(pagination: tuple[int, int] = Depends(get_pagination_params), session: Session = Depends(get_db_session)) -> list[SessionResponse]:
    session_service = SessionService(session)
    skip, limit = pagination
    sessions = session_service.list_all()[skip : skip + limit]
    return [
        SessionResponse(
            id=str(item.id),
            room_id=str(item.room_id),
            user_id=str(item.user_id),
            topic=item.topic,
            tags=item.tags,
            transcript=item.transcript,
            overall_score=item.overall_score,
            duration_seconds=item.duration_seconds,
        )
        for item in sessions
    ]


@router.get("/rooms/{room_id}", response_model=list[SessionResponse])
async def list_room_sessions(room_id: UUID, session: Session = Depends(get_db_session)) -> list[SessionResponse]:
    session_service = SessionService(session)
    items = session_service.list_sessions_for_room(room_id)
    return [
        SessionResponse(
            id=str(item.id),
            room_id=str(item.room_id),
            user_id=str(item.user_id),
            topic=item.topic,
            tags=item.tags,
            transcript=item.transcript,
            overall_score=item.overall_score,
            duration_seconds=item.duration_seconds,
        )
        for item in items
    ]
