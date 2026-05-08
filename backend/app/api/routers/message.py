from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlmodel import Session

from app.api.dependencies import get_db_session, get_pagination_params
from app.schemas import MessageCreateRequest, MessageResponse, TranscriptCreateRequest
from app.service.message import MessageService

router = APIRouter()


def _message_to_response(message) -> MessageResponse:
    return MessageResponse(
        id=str(message.id),
        room_id=str(message.room_id),
        user_id=str(message.user_id) if message.user_id else None,
        content=message.content,
        message_type=message.message_type,
        payload=message.payload,
    )


@router.get("/", response_model=list[MessageResponse])
async def list_messages(pagination: tuple[int, int] = Depends(get_pagination_params), session: Session = Depends(get_db_session)) -> list[MessageResponse]:
    message_service = MessageService(session)
    skip, limit = pagination
    messages = message_service.list_all()[skip : skip + limit]
    return [_message_to_response(m) for m in messages]


@router.get("/rooms/{room_id}", response_model=list[MessageResponse])
async def list_room_messages(room_id: UUID, session: Session = Depends(get_db_session), limit: int = Query(50, ge=1, le=200)) -> list[MessageResponse]:
    message_service = MessageService(session)
    messages = message_service.list_room_messages(room_id)
    return [_message_to_response(m) for m in messages[-limit:]]


@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(payload: MessageCreateRequest, session: Session = Depends(get_db_session)) -> MessageResponse:
    message_service = MessageService(session)
    message = message_service.create_transcript_message(UUID(payload.room_id), None, payload.content)
    message.message_type = message.message_type.TEXT
    saved_message = message_service.save(message)
    return _message_to_response(saved_message)


@router.post("/transcripts", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_transcript(payload: TranscriptCreateRequest, session: Session = Depends(get_db_session)) -> MessageResponse:
    message_service = MessageService(session)
    message = message_service.create_transcript_message(UUID(payload.room_id), UUID(payload.user_id), payload.content)
    return _message_to_response(message)
