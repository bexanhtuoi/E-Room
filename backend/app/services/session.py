import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlmodel import Session

from app.models import MessageRole
from app.repositories.message import message_crud
from app.repositories.room import room_crud
from app.repositories.session import SessionCrud, session_crud
from app.repositories.user import user_crud
from app.shared.exceptions import (
    AIServiceUnavailableError,
    BadRequestError,
    ExternalServiceError,
    NoScoredUtterancesError,
    NotAuthorizedError,
    SessionNotFoundError,
)
from app.utils.datetime_utils import as_naive_utc

__all__ = [
    "SessionCrud",
    "answer_session_question",
    "build_session_agent",
    "build_session_messages",
    "build_transcript",
    "collect_session_summaries",
    "count_sessions",
    "generate_session_feedback",
    "get_my_session",
    "get_session_chat_turns",
    "get_session_detail_data",
    "get_session_messages_data",
    "is_session_chat",
    "list_my_sessions",
    "parse_log_time",
    "recent_chat_context",
    "save_session_chat",
    "session_crud",
    "session_lines",
    "stream_session_answer",
    "summarize_scored_entry",
]


def is_session_chat(message) -> bool:
    try:
        return bool((json.loads(message.meta_data or "{}") or {}).get("session_chat"))
    except (TypeError, ValueError):
        return False


def session_lines(db: Session, db_session, limit: int = 500, with_ids: bool = False) -> list:
    """with_ids=True thêm message_id/user_id mỗi dòng (cho UI sửa câu).
    Agent/tools dùng mặc định False — shape cũ không đổi."""
    messages = message_crud.get_many(db, room_id=db_session.room_id, order_by="id", limit=limit)
    start = as_naive_utc(db_session.joined_at)
    end = as_naive_utc(db_session.left_at) if db_session.left_at is not None else None

    kept = []
    for message in messages:
        if is_session_chat(message):
            continue
        created = as_naive_utc(message.created_at)
        if created < start:
            continue
        if end is not None and created > end:
            continue
        kept.append(message)

    names = {}
    ids = {message.user_id for message in kept if message.user_id}
    for user in user_crud.get_by_ids(db, ids):
        names[user.id] = user.full_name or f"User {user.id}"

    lines = []
    for message in kept:
        if message.role == MessageRole.AI or not message.user_id:
            speaker = "AI"
        else:
            speaker = names.get(message.user_id, f"User {message.user_id}")
        line = {"speaker": speaker, "text": message.text}
        if with_ids:
            line["message_id"] = message.id
            line["user_id"] = message.user_id
        lines.append(line)

    return lines


def get_my_session(db: Session, session_id: int, user):
    db_session = session_crud.get_one(db, id=session_id)

    if db_session is None:
        raise SessionNotFoundError()

    if str(db_session.user_id) != str(user.id):
        room = room_crud.get_one(db, id=db_session.room_id)

        if room is None or (str(room.host_id) != str(user.id) and user.role != "admin"):
            raise NotAuthorizedError()

    return db_session


def list_my_sessions(db: Session, user) -> List[Dict[str, Any]]:
    items = []

    for db_session in session_crud.get_mine(db, user_id=user.id):
        room = room_crud.get_one(db, id=db_session.room_id)
        count = len(session_lines(db, db_session))
        items.append({"session": db_session, "room": room, "message_count": count})

    return items


def count_sessions(db: Session) -> int:
    return session_crud.count(db)


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


def build_session_agent(db_session, total_lines: int):
    from app.ai import get_agent
    from app.ai.llm.prompt import session_prompt
    from app.ai.llm.tools import TRANSCRIPT_TOOLS

    return get_agent(
        tools=TRANSCRIPT_TOOLS,
        prompt=session_prompt(db_session.id, total_lines),
    )


def build_session_messages(lines: list, full_question: str, tail: int = 50) -> list:
    from app.ai.llm.query import build_room_messages
    from app.ai.llm.tools import format_lines

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


def get_session_detail_data(db: Session, user, session_id: int) -> Dict[str, Any]:
    db_session = get_my_session(db, session_id, user)
    room = room_crud.get_one(db, id=db_session.room_id)
    _, count = build_transcript(db, db_session)

    return {"session": db_session, "room": room, "message_count": count}


def get_session_messages_data(db: Session, user, session_id: int) -> Dict[str, Any]:
    db_session = get_my_session(db, session_id, user)
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


async def answer_session_question(
    db: Session, db_session, user_id: int, question: str,
) -> tuple[str, int]:
    from app.ai.llm.query import run_query

    cleaned = (question or "").strip()

    if not cleaned:
        raise BadRequestError(detail="Câu hỏi không được để trống.")

    lines = session_lines(db, db_session)

    if not lines:
        raise BadRequestError(detail="Session chưa có tin nhắn nào.")

    full_question = recent_chat_context(db, db_session) + f"Current question:\n{cleaned}"
    messages = build_session_messages(lines, full_question)
    answer = await run_query(messages, agent=build_session_agent(db_session, len(lines)))

    if not answer:
        raise AIServiceUnavailableError(detail="AI chưa trả lời được ngay bây giờ.")

    save_session_chat(db, db_session, user_id, cleaned, answer)

    return answer, len(lines)


async def stream_session_answer(db: Session, db_session, user_id: int, question: str):
    from app.ai.llm.query import stream_events

    cleaned = (question or "").strip()
    lines = session_lines(db, db_session)

    if not cleaned:
        yield {"kind": "error", "text": "Câu hỏi không được để trống."}
        return

    if not lines:
        yield {"kind": "error", "text": "Session chưa có tin nhắn nào."}
        return

    full_question = recent_chat_context(db, db_session) + f"Current question:\n{cleaned}"
    messages = build_session_messages(lines, full_question)

    saw_token = False
    answer_parts = []

    try:
        async for event in stream_events(messages, agent=build_session_agent(db_session, len(lines))):
            if event.get("kind") == "token" and event.get("text"):
                saw_token = True
                answer_parts.append(event["text"])

            yield event
    except Exception:
        yield {"kind": "error", "text": "AI chưa trả lời được ngay bây giờ."}
        return

    if not saw_token:
        yield {"kind": "error", "text": "AI chưa trả lời được ngay bây giờ."}
        return

    save_session_chat(db, db_session, user_id, cleaned, "".join(answer_parts).strip())
    yield {"kind": "done", "message_count": len(lines)}


def parse_log_time(value) -> Optional[datetime]:
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


def summarize_scored_entry(entry: dict) -> dict:
    """Rút gọn 1 utterance đã chấm cho prompt session: chỉ điểm + từ sai,
    không bê nguyên phoneme list (giữ prompt gọn)."""
    pron = entry.get("pronunciation") or {}
    report = pron.get("report") or {}
    scores = report.get("scores") or {}
    bad_words = []
    for word in report.get("word_details") or []:
        if (word.get("status") or "ok") != "ok" and len(bad_words) < 5:
            bad_words.append({
                "word": word.get("word"),
                "score": word.get("score"),
                "status": word.get("status"),
                "expected_ipa": word.get("expected_ipa"),
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


def collect_session_summaries(db: Session, db_session) -> tuple[list, int]:
    from app.ai.stt.speech_log import read_user_log
    from app.repositories.pronunciation_score import pronunciation_score_crud

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
        summaries.append(summarize_scored_entry({
            "corrected_text": row.scored_text,
            "pronunciation": {"score": row.overall, "report": report},
        }))

    total_utterances = len(rows)
    if not summaries:
        # Fallback: điểm chấm trước khi deploy bảng DB (vẫn nằm trong JSONL).
        entries = read_user_log(db_session.room_id, db_session.user_id)
        in_window = []
        for entry in entries:
            created = parse_log_time(entry.get("created_at"))
            if created is None or created < start:
                continue
            if end is not None and created > end:
                continue
            in_window.append(entry)
        total_utterances = len(in_window)
        summaries = [summarize_scored_entry(entry) for entry in in_window
                     if (entry.get("pronunciation") or {}).get("report")]

    return summaries, total_utterances


def generate_session_feedback(
    db: Session,
    user,
    session_id: int,
    model: str = "",
    temperature: float = 0.6,
    max_tokens: int = 2000,
) -> Dict[str, Any]:
    """AI feedbacks cấp session (prompt gọn chỉ mô tả phần sai).
    Không chấm lại, không nhận audio."""
    from app.ai.pronunciation import SESSION_FEEDBACK_PROMPT, request_pronun_feedback

    db_session = get_my_session(db, session_id, user)
    summaries, total_utterances = collect_session_summaries(db, db_session)

    if not summaries:
        raise NoScoredUtterancesError()

    payload = {
        "session_id": session_id,
        "utterances": summaries,
    }
    try:
        feedback = request_pronun_feedback(
            scoring_report=payload,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system_prompt=SESSION_FEEDBACK_PROMPT,
            user_label="session_scores",
        )
    except NotImplementedError as error:
        raise AIServiceUnavailableError(detail=str(error))
    except Exception as error:
        raise ExternalServiceError(detail=f"Lỗi nhận xét session: {error}")

    return {
        "session_id": session_id,
        "scored_count": len(summaries),
        "total_utterances": total_utterances,
        "feedback": feedback,
    }
