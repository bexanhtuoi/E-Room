import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.ai import get_agent
from app.ai.prompt import session_prompt
from app.ai.pronunciation import SESSION_FEEDBACK_PROMPT, request_pronun_feedback
from app.ai.query import build_room_messages, run_query, stream_events
from app.ai.tools import TRANSCRIPT_TOOLS, format_lines
from app.api.dependencies import require_auth
from app.database import get_session
from app.models import MessageRole
from app.schemas import (
    MySessionsResponse,
    SessionAnswerResponse,
    SessionAskRequest,
    SessionWithRoom,
)
from app.schemas.speech import SpeechFeedbackRequest
from app.services import message_crud, room_crud, session_crud, user_crud
from app.services.session import session_lines
from app.utils.datetime_utils import as_naive_utc

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


def save_session_chat(db: Session, db_session, user_id: int, question: str, answer: str) -> None:

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
            turns.append({"role": "user" if message.role == MessageRole.USER else "ai", "text": message.text, "user_id": message.user_id})
    return turns


def build_transcript(db: Session, db_session) -> tuple[str, int]:
    lines = session_lines(db, db_session)
    return "\n".join(f"{line['speaker']}: {line['text']}" for line in lines), len(lines)


def build_agent(db_session, total_lines: int):
    return get_agent(
        tools=TRANSCRIPT_TOOLS,
        prompt=session_prompt(db_session.id, total_lines),
    )


def build_session_messages(lines: list, full_question: str, tail: int = 50) -> list:
    history = [format_lines(lines[-tail:])] if lines else []
    return build_room_messages(history, full_question)


def recent_chat_context(db: Session, db_session, limit: int = 20) -> str:
    turns = get_session_chat_turns(db, db_session)[-limit:]
    if not turns:
        return ""
    cache: dict = {}
    lines = []
    for turn in turns:
        if turn["role"] == "user":
            user_id = turn.get("user_id")
            if user_id not in cache:
                user = user_crud.get_one(db, id=user_id) if user_id else None
                cache[user_id] = (getattr(user, "full_name", None) or f"User {user_id}") if user_id else "You"
            speaker = cache[user_id]
        else:
            speaker = "AI"
        lines.append(f"{speaker}: {turn['text']}")
    return "Recent questions in this chat (newest last):\n" + "\n".join(lines) + "\n\n"


@router.get("/count")
def count_sessions(
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
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
        count = len(session_lines(db, db_session))
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
    transcript_lines = [
        {"speaker": line["speaker"], "text": line["text"],
         "message_id": line.get("message_id"), "user_id": line.get("user_id")}
        for line in session_lines(db, db_session, with_ids=True)
    ]

    return {
        "session_id": session_id,
        "message_count": count,
        "transcript": transcript,
        "transcript_lines": transcript_lines,
        "chat": get_session_chat_turns(db, db_session),
    }


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
    lines = session_lines(db, db_session)
    if not lines:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No messages in this session yet")

    full_question = recent_chat_context(db, db_session) + f"Current question:\n{question}"
    messages = build_session_messages(lines, full_question)
    answer = await run_query(messages, agent=build_agent(db_session, len(lines)))
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
    question = (ask_in.question or "").strip()
    db_session = get_my_session(db, session_id, request)
    lines = session_lines(db, db_session)

    async def event_source():
        if not question:
            yield f"data: {json.dumps({'kind': 'error', 'text': 'Question must not be empty'})}\n\n"
            return
        if not lines:
            yield f"data: {json.dumps({'kind': 'error', 'text': 'No messages in this session yet'})}\n\n"
            return

        saw_token = False
        answer_parts = []
        full_question = recent_chat_context(db, db_session) + f"Current question:\n{question}"
        messages = build_session_messages(lines, full_question)
        try:
            async for event in stream_events(messages, agent=build_agent(db_session, len(lines))):
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


def _parse_log_time(value) -> Optional[datetime]:
    """created_at trong speech log là ISO string (có tz). Trả về naive UTC để
    so được với Session.joined_at/left_at (DB lưu naive UTC)."""
    if not value:
        return None
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


def _summarize_scored_entry(entry: dict) -> dict:
    """Rút gọn 1 utterance đã chấm cho prompt session: chỉ điểm + từ sai,
    không bê nguyên phoneme list (giữ prompt gọn)."""
    pron = entry.get("pronunciation") or {}
    report = pron.get("report") or {}
    scores = report.get("scores") or {}
    bad_words = []
    for w in report.get("word_details") or []:
        if (w.get("status") or "ok") != "ok" and len(bad_words) < 5:
            bad_words.append({
                "word": w.get("word"),
                "score": w.get("score"),
                "status": w.get("status"),
                "expected_ipa": w.get("expected_ipa"),
            })
    return {
        "text": entry.get("corrected_text") or entry.get("text", ""),
        "overall": round(float(scores.get("overall", pron.get("score", 0.0) or 0.0)), 1),
        "sounds": scores.get("sounds"),
        "stress": scores.get("stress"),
        "fluency": scores.get("fluency"),
        "completeness": scores.get("completeness"),
        "bad_words": bad_words,
        "top_errors": (report.get("top_errors") or (pron.get("details") or {}).get("top_errors") or [])[:5],
    }


@router.post("/{session_id}/feedback")
def session_feedback(
    session_id: int,
    request: Request,
    body: Optional[SpeechFeedbackRequest] = None,
    db: Session = Depends(get_session),
    _: str = Depends(require_auth),
) -> dict:
    """AI feedbacks cấp session (LLM local, prompt gọn chỉ mô tả phần sai).

    Gộp các câu của CHÍNH user trong khoảng joined_at–left_at của session mà
    đã có pronunciation.report, gửi LLM với SESSION_FEEDBACK_PROMPT.
    Không chấm lại, không nhận audio. Chưa có câu nào được chấm → 409.

    Nguồn điểm: bảng pronunciation_scores (máy host tính local, write-through
    ở POST .../score). JSONL speech log chỉ là fallback cho điểm chấm từ
    trước khi có bảng DB."""
    from app.ai.speech_log import read_user_log
    from app.services.pronunciation_score import pronunciation_score_crud

    db_session = get_my_session(db, session_id, request)
    start = as_naive_utc(db_session.joined_at)
    end = as_naive_utc(db_session.left_at) if db_session.left_at is not None else None

    rows = pronunciation_score_crud.scored_in_window(
        db, db_session.room_id, db_session.user_id, start, end,
        session_id=db_session.id,
    )
    summaries = []
    for row in rows:
        try:
            report = json.loads(row.report_json or "{}")
        except (TypeError, ValueError):
            report = {}
        summaries.append(_summarize_scored_entry({
            "corrected_text": row.scored_text,
            "pronunciation": {"score": row.overall, "report": report},
        }))

    total_utterances = len(rows)
    if not summaries:
        # Fallback: điểm chấm trước khi deploy bảng DB (vẫn nằm trong JSONL).
        entries = read_user_log(db_session.room_id, db_session.user_id)
        in_window = []
        for entry in entries:
            created = _parse_log_time(entry.get("created_at"))
            if created is None or created < start:
                continue
            if end is not None and created > end:
                continue
            in_window.append(entry)
        total_utterances = len(in_window)
        summaries = [_summarize_scored_entry(e) for e in in_window
                     if (e.get("pronunciation") or {}).get("report")]
    if not summaries:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Chưa có câu nào được chấm điểm trong session này — chấm điểm từng câu trước (POST .../speech-logs/{message_id}/score).",
        )
    payload = {
        "session_id": session_id,
        "utterances": summaries,
    }
    opts = body or SpeechFeedbackRequest()
    try:
        feedback = request_pronun_feedback(
            scoring_report=payload,
            model=opts.model or "",
            temperature=opts.temperature if opts.temperature is not None else 0.6,
            max_tokens=opts.max_tokens if opts.max_tokens is not None else 2000,
            system_prompt=SESSION_FEEDBACK_PROMPT,
            user_label="session_scores",
        )
    except NotImplementedError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error))
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Session feedback lỗi: {error}")
    return {
        "session_id": session_id,
        "scored_count": len(summaries),
        "total_utterances": total_utterances,
        "feedback": feedback,
    }
