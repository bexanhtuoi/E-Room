from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.dependencies import get_pagination_params
from app.schemas import MessageCreateRequest, MessageResponse, TranscriptCreateRequest
from app.service.message import MessageService

router = APIRouter()
message_service = MessageService()


@router.get("/", response_model=list[MessageResponse])
async def list_messages(pagination: tuple[int, int] = Depends(get_pagination_params)) -> list[MessageResponse]:
    skip, limit = pagination
    messages = message_service.list_all()[skip : skip + limit]
    return [
        MessageResponse(
            id=str(message.id),
            room_id=message.room_id,
            user_id=message.user_id,
            content=message.content,
            message_type=message.message_type,
            metadata=message.metadata,
        )
        for message in messages
    ]


@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(payload: MessageCreateRequest) -> MessageResponse:
    message = message_service.create_transcript_message(payload.room_id, "system", payload.content)
    message.message_type = message.message_type.TEXT
    saved_message = message_service.save(message)
    return MessageResponse(
        id=str(saved_message.id),
        room_id=saved_message.room_id,
        user_id=saved_message.user_id,
        content=saved_message.content,
        message_type=saved_message.message_type,
        metadata=saved_message.metadata,
    )


@router.post("/transcripts", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_transcript(payload: TranscriptCreateRequest) -> MessageResponse:
    message = message_service.create_transcript_message(payload.room_id, payload.user_id, payload.content)
    return MessageResponse(
        id=str(message.id),
        room_id=message.room_id,
        user_id=message.user_id,
        content=message.content,
        message_type=message.message_type,
        metadata=message.metadata,
    )
