import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
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


def is_session_chat(message) -> bool:
    # Tin Q&A voi Session AI — luu trong bang messages nhung khong phai
    # transcript phong noi (khong dem vao session lines / room chat).
    try:
        return bool((json.loads(message.meta_data or "{}") or {}).get("session_chat"))
    except (TypeError, ValueError):
        return False


def save_session_chat(db: Session, db_session, user_id: int, question: str, answer: str) -> None:
    # Luu lich su hoi dap de F5 van con, nhan meta session de phan biet.
    meta = json.dumps({"session_chat": True, "session_id": db_session.id})
    message_crud.create(
        db,
        obj_in={"room_id": db_session.room_id, "user_id": user_id, "role": MessageRole.USER, "text": question, "meta_data": meta},
    )
    message_crud.create(
        db,
        obj_in={"room_id": db_session.room_id, "user_id": None, "role": MessageRole.AI, "text": answer, "meta_data": meta},
    )


def get_session_chat_turns(db: Session, db_session) -> list:
    turns = []
    for message in message_crud.get_many(db, room_id=db_session.room_id, order_by="id", limit=500):
        try:
            meta = json.loads(message.meta_data or "{}") or {}
        except (TypeError, ValueError):
            continue
        if meta.get("session_chat") and meta.get("session_id") == db_session.id:
            turns.append({"role": "user" if message.role == MessageRole.USER else "ai", "text": message.text})
    return turns


def build_session_lines(db: Session, db_session) -> list:
    messages = message_crud.get_many(db, room_id=db_session.room_id, order_by="id", limit=500)
    start = db_session.joined_at.replace(tzinfo=None) if getattr(db_session.joined_at, "tzinfo", None) else db_session.joined_at
    end = db_session.left_at
    if end is not None and getattr(end, "tzinfo", None):
        end = end.replace(tzinfo=None)

    lines = []
    cache: dict = {}
    for message in messages:
        if is_session_chat(message):
            continue
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
            if not is_session_chat(message)
            and (message.created_at.replace(tzinfo=None) if getattr(message.created_at, "tzinfo", None) else message.created_at) >= start
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

    return {"session_id": session_id, "message_count": count, "transcript": transcript, "chat": get_session_chat_turns(db, db_session)}


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

    save_session_chat(db, db_session, request.state.current_user.id, question, answer)

    return SessionAnswerResponse(answer=answer, message_count=len(lines))


@router.post("/{session_id}/chat/stream")
async def chat_session_stream(
    session_id: int,
    ask_in: SessionAskRequest,
    request: Request,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
):
    # Stream thinking + tool call + token giong @ai trong phong (SSE).
    question = (ask_in.question or "").strip()
    db_session = get_my_session(db, session_id, request)
    lines = build_session_lines(db, db_session)

    async def event_source():
        if not question:
            yield f"data: {json.dumps({'kind': 'error', 'text': 'Question must not be empty'})}\n\n"
            return
        if not lines:
            yield f"data: {json.dumps({'kind': 'error', 'text': 'No messages in this session yet'})}\n\n"
            return

        saw_token = False
        answer_parts = []
        try:
            async for event in session_agent.stream_session_agent(question, lines):
                if event.get("kind") == "token" and event.get("text"):
                    saw_token = True
                    answer_parts.append(event["text"])
                yield f"data: {json.dumps(event)}\n\n"
        except Exception:
            yield f"data: {json.dumps({'kind': 'error', 'text': 'AI could not answer right now'})}\n\n"
            return

        if not saw_token:
            yield f"data: {json.dumps({'kind': 'error', 'text': 'AI could not answer right now'})}\n\n"
            return

        save_session_chat(db, db_session, request.state.current_user.id, question, "".join(answer_parts).strip())
        yield f"data: {json.dumps({'kind': 'done', 'message_count': len(lines)})}\n\n"

    return StreamingResponse(event_source(), media_type="text/event-stream")
