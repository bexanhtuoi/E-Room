from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlmodel import Session

from app.ai import session_agent
from app.api.dependencies import require_auth
from app.database import get_session
from app.models import MessageRole
from app.schemas import (
    MySessionsResponse,
    SessionAnswerResponse,
    SessionAskRequest,
    SessionWithRoom,
)
from app.services import message_crud, room_crud, session_crud, user_crud

router = APIRouter()


def get_my_session(db: Session, session_id: int, request: Request):
    db_session = session_crud.get_one(db, id=session_id)
    if not db_session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    current_user = request.state.current_user
    if str(db_session.user_id) != str(current_user.id):
        room = room_crud.get_one(db, id=db_session.room_id)
        if not room or (str(room.host_id) != str(current_user.id) and current_user.role != "admin"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    return db_session


def build_session_lines(db: Session, db_session) -> list:
    messages = message_crud.get_many(db, room_id=db_session.room_id, order_by="id", limit=500)
    start = db_session.joined_at.replace(tzinfo=None) if getattr(db_session.joined_at, "tzinfo", None) else db_session.joined_at
    end = db_session.left_at
    if end is not None and getattr(end, "tzinfo", None):
        end = end.replace(tzinfo=None)

    lines = []
    cache: dict = {}
    for message in messages:
        created = message.created_at.replace(tzinfo=None) if getattr(message.created_at, "tzinfo", None) else message.created_at
        if created < start:
            continue
        if end is not None and created > end:
            continue
        if message.user_id not in cache:
            speaker = cache[message.user_id] = (
                user_crud.get_one(db, id=message.user_id).full_name if message.user_id else "AI"
            ) or f"User {message.user_id}"
        else:
            speaker = cache[message.user_id]
        if message.role == MessageRole.AI:
            speaker = "AI"
        lines.append({"speaker": speaker, "text": message.text})

    return lines


def build_transcript(db: Session, db_session) -> tuple[str, int]:
    lines = build_session_lines(db, db_session)
    return "\n".join(f"{line['speaker']}: {line['text']}" for line in lines), len(lines)


@router.get("/count")
def count_sessions(db: Session = Depends(get_session)) -> dict:
    return {"count": session_crud.count(db)}


@router.get("/mine", response_model=MySessionsResponse)
def get_my_sessions(
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> MySessionsResponse:
    current_user = request.state.current_user
    items = []
    for db_session in session_crud.get_mine(db, user_id=current_user.id):
        room = room_crud.get_one(db, id=db_session.room_id)
        start = db_session.joined_at.replace(tzinfo=None) if getattr(db_session.joined_at, "tzinfo", None) else db_session.joined_at
        end = db_session.left_at
        if end is not None and getattr(end, "tzinfo", None):
            end = end.replace(tzinfo=None)
        count = sum(
            1
            for message in message_crud.get_many(db, room_id=db_session.room_id, order_by="id", limit=500)
            if (message.created_at.replace(tzinfo=None) if getattr(message.created_at, "tzinfo", None) else message.created_at) >= start
            and (end is None or (message.created_at.replace(tzinfo=None) if getattr(message.created_at, "tzinfo", None) else message.created_at) <= end)
        )
        items.append(SessionWithRoom(session=db_session, room=room, message_count=count))

    return MySessionsResponse(sessions=items)


@router.get("/{session_id}", response_model=SessionWithRoom)
def get_session_detail(
    session_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> SessionWithRoom:
    db_session = get_my_session(db, session_id, request)
    room = room_crud.get_one(db, id=db_session.room_id)
    transcript, count = build_transcript(db, db_session)

    return SessionWithRoom(session=db_session, room=room, message_count=count)


@router.get("/{session_id}/messages")
def get_session_messages(
    session_id: int,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    db_session = get_my_session(db, session_id, request)
    transcript, count = build_transcript(db, db_session)

    return {"session_id": session_id, "message_count": count, "transcript": transcript}


@router.post("/{session_id}/chat", response_model=SessionAnswerResponse)
async def chat_session(
    session_id: int,
    ask_in: SessionAskRequest,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> SessionAnswerResponse:
    question = (ask_in.question or "").strip()
    if not question:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question must not be empty")

    db_session = get_my_session(db, session_id, request)
    lines = build_session_lines(db, db_session)
    if not lines:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No messages in this session yet")

    answer = await session_agent.run_session_agent(question, lines)
    if not answer:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI could not answer right now")

    return SessionAnswerResponse(answer=answer, message_count=len(lines))
