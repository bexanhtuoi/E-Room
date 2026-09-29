from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlmodel import Session

from app.api.dependencies import get_pagination_params, require_auth
from app.database import get_session
from app.schemas import MessageCreateSchema, MessageResponse
from app.services.message import message_service

router = APIRouter()


@router.get("/", response_model=List[MessageResponse])
def get_messages(
    request: Request,
    room_id: Optional[int] = Query(None, description="Filter messages by room_id"),
    user_id: Optional[int] = Query(None, description="Filter messages by user_id"),
    role: Optional[str] = Query(None, description="Filter messages by role (user/ai)"),
    db: Session = Depends(get_session),
    pagination: tuple[int, int] = Depends(get_pagination_params),
    _: str = Depends(require_auth),
) -> List[MessageResponse]:
    skip, limit = pagination

    return message_service.list_messages(
        db, request.state.current_user,
        room_id=room_id, user_id=user_id, role=role, skip=skip, limit=limit,
    )


@router.get("/count")
def count_messages(
    request: Request,
    room_id: Optional[int] = Query(None, description="Filter count by room_id"),
    user_id: Optional[int] = Query(None, description="Filter count by user_id"),
    role: Optional[str] = Query(None, description="Filter count by role"),
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    count = message_service.count_messages(
        db, request.state.current_user, room_id=room_id, user_id=user_id, role=role,
    )

    return {"count": count}


@router.get("/{message_id}", response_model=MessageResponse)
def get_message(
    message_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> MessageResponse:
    return message_service.get_message_data(db, request.state.current_user, message_id)


@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(
    message_in: MessageCreateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> MessageResponse:
    return message_service.create_message(db, request.state.current_user, message_in)


@router.delete("/{message_id}", response_model=MessageResponse)
def delete_message(
    message_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> MessageResponse:
    return message_service.delete_message(db, request.state.current_user, message_id)
