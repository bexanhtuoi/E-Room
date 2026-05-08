from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.api.dependencies import get_db_session, get_pagination_params
from app.schemas import MessageCreateRequest, MessageResponse, TranscriptCreateRequest
from app.service.message import MessageService

router = APIRouter()


@router.get("/", response_model=list[MessageResponse])
async def list_messages(pagination: tuple[int, int] = Depends(get_pagination_params), session: Session = Depends(get_db_session)) -> list[MessageResponse]:
    message_service = MessageService(session)
    skip, limit = pagination
    messages = message_service.list_all()[skip : skip + limit]
    return [
        MessageResponse(
            id=str(message.id),
            room_id=str(message.room_id),
            user_id=str(message.user_id) if message.user_id else None,
            content=message.content,
            message_type=message.message_type,
            payload=message.payload,
        )
        for message in messages
    ]


@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(payload: MessageCreateRequest, session: Session = Depends(get_db_session)) -> MessageResponse:
    message_service = MessageService(session)
    message = message_service.create_transcript_message(UUID(payload.room_id), None, payload.content)
    message.message_type = message.message_type.TEXT
    saved_message = message_service.save(message)
    return MessageResponse(
        id=str(saved_message.id),
        room_id=str(saved_message.room_id),
        user_id=str(saved_message.user_id) if saved_message.user_id else None,
        content=saved_message.content,
        message_type=saved_message.message_type,
        payload=saved_message.payload,
    )


@router.post("/transcripts", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_transcript(payload: TranscriptCreateRequest, session: Session = Depends(get_db_session)) -> MessageResponse:
    message_service = MessageService(session)
    message = message_service.create_transcript_message(UUID(payload.room_id), UUID(payload.user_id), payload.content)
    return MessageResponse(
        id=str(message.id),
        room_id=str(message.room_id),
        user_id=str(message.user_id) if message.user_id else None,
        content=message.content,
        message_type=message.message_type,
        payload=message.payload,
    )
