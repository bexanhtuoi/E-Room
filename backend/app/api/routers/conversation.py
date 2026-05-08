from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import get_pagination_params
from app.schemas import SessionResponse
from app.service.conversation import SessionService

router = APIRouter()
session_service = SessionService()


@router.get("/", response_model=list[SessionResponse])
async def list_sessions(pagination: tuple[int, int] = Depends(get_pagination_params)) -> list[SessionResponse]:
    skip, limit = pagination
    sessions = session_service.list_all()[skip : skip + limit]
    return [
        SessionResponse(
            id=str(session.id),
            room_id=session.room_id,
            user_id=session.user_id,
            topic=session.topic,
            tags=session.tags,
            transcript=session.transcript,
            overall_score=session.overall_score,
            duration_seconds=session.duration_seconds,
        )
        for session in sessions
    ]
