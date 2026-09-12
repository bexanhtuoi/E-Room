from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import Session

from app.ai.tasks import enqueue_ai_job, mark_room_activity
from app.api.dependencies import authorize_owner, authorize_room_access, get_pagination_params, require_auth
from app.database import get_session
from app.models import MessageRole
from app.schemas import MessageCreateSchema, MessageResponse
from app.services import message_crud, room_crud
from app.services.session import is_session_chat

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

    if room_id is not None:
        db_room = room_crud.get_one(db, id=room_id)
        if db_room is not None:
            authorize_room_access(db_room, request)

    filter_kwargs = {}
    if room_id is not None:
        filter_kwargs["room_id"] = room_id
    if user_id is not None:
        filter_kwargs["user_id"] = user_id
    if role is not None:
        filter_kwargs["role"] = role

    # Moi nhat truoc: history load + poll limit moi thay tin moi,
    # khong thi phong dong (>limit tin) se mat tin moi + poll vo dung.
    messages = message_crud.get_many(db, skip=skip, limit=limit, order_by="id", desc=True, **filter_kwargs)
    # An tin Q&A voi Session AI (meta session_chat) — chi doc trong /session/:id.
    return [message for message in messages if not is_session_chat(message)]


@router.get("/count")
def count_messages(
    request: Request,
    room_id: Optional[int] = Query(None, description="Filter count by room_id"),
    user_id: Optional[int] = Query(None, description="Filter count by user_id"),
    role: Optional[str] = Query(None, description="Filter count by role"),
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    if room_id is not None:
        db_room = room_crud.get_one(db, id=room_id)
        if db_room is not None:
            authorize_room_access(db_room, request)

    filter_kwargs = {}
    if room_id is not None:
        filter_kwargs["room_id"] = room_id
    if user_id is not None:
        filter_kwargs["user_id"] = user_id
    if role is not None:
        filter_kwargs["role"] = role

    return {"count": message_crud.count(db, **filter_kwargs)}


@router.get("/{message_id}", response_model=MessageResponse)
def get_message(message_id: int, db: Session = Depends(get_session)) -> MessageResponse:
    db_message = message_crud.get_one(db, id=message_id)
    if not db_message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")
    return db_message


@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def create_message(
    message_in: MessageCreateSchema,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> MessageResponse:
    obj_in_data = message_in.model_dump()
    obj_in_data["user_id"] = request.state.current_user.id
    obj_in_data["role"] = MessageRole.USER
    new_message = message_crud.create(db, obj_in=obj_in_data)

    mark_room_activity(message_in.room_id)
    if message_in.text.lstrip().lower().startswith("@ai"):
        query = message_in.text.lstrip()[3:].strip()
        if query:
            enqueue_ai_job(
                message_in.room_id,
                "answer",
                query,
                new_message.id,
            )

    return new_message


@router.delete("/{message_id}", response_model=MessageResponse)
def delete_message(
    message_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> MessageResponse:
    db_message = message_crud.get_one(db, id=message_id)
    if not db_message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    authorize_owner(db_message.user_id, request)

    deleted_message = message_crud.delete(db, db_obj=db_message)
    return deleted_message
