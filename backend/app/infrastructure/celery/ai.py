from __future__ import annotations

import asyncio
import json
from datetime import date, timedelta
from uuid import uuid4

from celery import shared_task
from sqlmodel import Session as DBSession, text

from app.agent.corrector import correct_text
from app.agent.heartbeat import generate_heartbeat as generate_room_heartbeat
from app.agent.llm import get_llm
from app.config import settings
from app.database import engine
from app.infrastructure.audio import AudioProcessor
from app.infrastructure.redis_client import get_redis_client
from app.log import get_logger
from app.model.common import SubscriptionTier
from app.model.conversation import Session as RoomSession

logger = get_logger(__name__)

@shared_task(name="eroom.generate_ai_correction", bind=True, max_retries=3, default_retry_delay=5)
def generate_ai_correction(self, text: str, user_id: str, room_id: str,
                           pronunciation: dict | None = None) -> dict:
    logger.info("Bắt đầu sửa lỗi (Celery)", extra={"user_id": user_id, "text_len": len(text)})
    try:
        result = asyncio.run(correct_text(text, user_id, pronunciation))
        _publish_result("room:correction", room_id, user_id, result)
        return result
    except Exception as e:
        logger.error("Sửa lỗi thất bại (Celery)", exc_info=True)
        raise self.retry(exc=e)

@shared_task(name="eroom.transcribe_audio", bind=True, max_retries=3, default_retry_delay=10)
def transcribe_audio(self, audio_data: bytes, user_id: str, room_id: str,
                     sample_rate: int = 16000) -> dict:
    logger.info("Bắt đầu nhận dạng giọng nói (Celery)", extra={"user_id": user_id, "audio_bytes": len(audio_data)})
    try:
        from app.infrastructure.audio_pipeline import PronunciationPipeline
        pipeline = PronunciationPipeline()
        result = asyncio.run(pipeline.assess(audio_data, sample_rate=sample_rate))
        payload = {
            "text": result["text"],
            "user_id": user_id,
            "scores": result["scores"],
            "needs_remediation": result["needs_remediation"],
        }
        _publish_result("room:transcript", room_id, user_id, payload)
        if payload["text"]:
            generate_ai_correction.delay(payload["text"], user_id, room_id, payload.get("scores"))
        return payload
    except Exception as e:
        logger.error("Nhận dạng giọng nói thất bại (Celery)", exc_info=True)
        payload = {"text": "", "user_id": user_id, "scores": None, "needs_remediation": False}
        _publish_result("room:transcript", room_id, user_id, payload)
        return payload

@shared_task(name="eroom.generate_heartbeat", bind=True, max_retries=2, default_retry_delay=30)
def generate_heartbeat(
    self, room_id: str, topic: str, tags: list[str] | None = None,
    recent_messages: list[dict] | None = None, heartbeat_count: int = 1,
) -> dict:
    try:
        result = asyncio.run(generate_room_heartbeat(room_id, topic, tags, recent_messages, heartbeat_count))
        _publish_result("room:heartbeat", room_id, "", result)
        return result
    except Exception as e:
        logger.error("Nhịp tim thất bại (Celery)", exc_info=True)
        raise self.retry(exc=e)


@shared_task(name="eroom.classify_intent", bind=True, max_retries=2, default_retry_delay=10)
def classify_intent(self, query: str, room_tags: list[str], user_id: str = "") -> dict:
    logger.info("Bắt đầu phân loại ý định (Celery)", extra={"user_id": user_id, "query_len": len(query)})
    try:
        llm = get_llm()
        prompt = (
            "Classify the user query into exactly one intent category.\n\n"
            f"Room tags: {', '.join(room_tags) if room_tags else 'general English practice'}\n"
            f"User query: \"{query}\"\n\n"
            "Possible intents:\n"
            "- english_practice: asking about English language (grammar, vocabulary, pronunciation, corrections)\n"
            "- tag_discussion: discussing topics related to room tags\n"
            "- code_request: asking to write, debug, or explain code\n"
            "- personal_task: unrelated personal errand or request\n"
            "- harmful: hate speech, harassment, threats, illegal content\n"
            "- unsure: genuinely ambiguous intent\n\n"
            'Return ONLY a JSON object: {"intent": "<label>", "confidence": <float 0.0-1.0>}'
        )
        response = asyncio.run(llm.ainvoke(prompt))
        content = response.content if hasattr(response, "content") else str(response)
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        result = json.loads(content)
        logger.info("Phân loại ý định hoàn tất (Celery)", extra={"intent": result.get("intent"), "user_id": user_id})
        return result
    except Exception:
        logger.error("Phân loại ý định thất bại (Celery)", exc_info=True)
        return {"intent": "unsure", "confidence": 0.0}

@shared_task(name="eroom.generate_session_note", bind=True, max_retries=2, default_retry_delay=30)
def generate_session_note(self, session_id: str, user_id: str) -> dict:
    logger.info("Bắt đầu tạo ghi chú phiên (Celery)", extra={"session_id": session_id, "user_id": user_id})
    try:
        with DBSession(engine) as session:
            if not _check_pro_plus(session, user_id):
                return {"status": "skipped", "reason": "not_pro_plus"}

            room_session = session.get(RoomSession, session_id)
            if room_session is None:
                return {"status": "error", "message": "session not found"}

            transcript_text = _extract_transcript_text(room_session)
            corrections_text = _extract_corrections_text(room_session)

            note_prompt = _build_note_prompt(room_session, transcript_text, corrections_text)
            llm = get_llm()
            response = asyncio.run(llm.ainvoke(note_prompt))
            note_content = response.content if hasattr(response, "content") else str(response)

            note_id = str(uuid4())
            _save_session_note(session, note_id, user_id, session_id, room_session, note_content)
            session.commit()

        logger.info("Tạo ghi chú phiên hoàn tất (Celery)", extra={"session_id": session_id, "note_id": note_id})
        return {"status": "completed", "note_id": note_id, "word_count": len(note_content.split())}
    except Exception as e:
        logger.error("Tạo ghi chú phiên thất bại (Celery)", exc_info=True)
        raise self.retry(exc=e)


def _check_pro_plus(session: DBSession, user_id: str) -> bool:
    sub = session.exec(
        text("SELECT * FROM subscriptions WHERE user_id = :uid ORDER BY created_at DESC LIMIT 1"),
        {"uid": user_id},
    ).first()
    tier = sub.tier if sub else "free"
    try:
        tier_enum = SubscriptionTier(tier)
    except ValueError:
        tier_enum = SubscriptionTier.FREE
    return tier_enum in (SubscriptionTier.PRO_PLUS,)


def _extract_transcript_text(room_session: RoomSession) -> str:
    if not hasattr(room_session, "full_transcript") or not room_session.full_transcript:
        return ""
    transcript_data = (
        json.loads(room_session.full_transcript)
        if isinstance(room_session.full_transcript, str)
        else room_session.full_transcript
    )
    if not isinstance(transcript_data, list):
        return ""
    return " ".join(
        m.get("text", "") if isinstance(m, dict) else str(m)
        for m in transcript_data
    )


def _extract_corrections_text(room_session: RoomSession) -> str:
    if not hasattr(room_session, "corrections") or not room_session.corrections:
        return ""
    corrections_data = (
        json.loads(room_session.corrections)
        if isinstance(room_session.corrections, str)
        else room_session.corrections
    )
    if not isinstance(corrections_data, list):
        return ""
    return "\n".join(
        f"- {c.get('original', '')} \u2192 {c.get('corrected', '')}: {c.get('explanation', '')}"
        for c in corrections_data if isinstance(c, dict)
    )


def _build_note_prompt(
    room_session: RoomSession,
    transcript_text: str,
    corrections_text: str,
) -> str:
    topic = room_session.topic or "English Practice"
    tags_str = ", ".join(room_session.tags) if hasattr(room_session, "tags") and room_session.tags else "general"
    transcript_preview = transcript_text[:3000] if transcript_text else "(no transcript)"
    corrections_preview = corrections_text[:2000] if corrections_text else "(no corrections)"
    return (
        "You are an English learning assistant. Create a structured session note in Markdown.\n\n"
        f"Session topic: {topic}\n"
        f"Tags: {tags_str}\n\n"
        "## Transcript excerpts:\n"
        f"{transcript_preview}\n\n"
        "## Corrections:\n"
        f"{corrections_preview}\n\n"
        "Generate a session note with these sections (use ## headers):\n"
        "## Summary\nA brief 2-3 sentence summary of what was discussed.\n\n"
        "## New Vocabulary\nList 3-5 new words or phrases the learner encountered (if any).\n\n"
        "## Key Corrections\nList the most important grammar/vocabulary corrections (top 3-5).\n\n"
        "## Strengths\nWhat the learner did well.\n\n"
        "## Areas to Improve\nSpecific areas for improvement.\n\n"
        "## Recommended Practice\n1-2 concrete practice suggestions.\n\n"
        "Return only the Markdown note, no preamble."
    )


def _save_session_note(
    session: DBSession,
    note_id: str,
    user_id: str,
    session_id: str,
    room_session: RoomSession,
    note_content: str,
) -> None:
    tags_str = ",".join(room_session.tags) if hasattr(room_session, "tags") and room_session.tags else ""
    session.exec(
        text(
            "INSERT INTO session_notes (id, user_id, session_id, content, tags, word_count, created_at, updated_at) "
            "VALUES (:id, :uid, :sid, :content, :tags, :wc, NOW(), NOW())"
        ),
        {
            "id": note_id,
            "uid": user_id,
            "sid": session_id,
            "content": note_content,
            "tags": tags_str,
            "wc": len(note_content.split()),
        },
    )

@shared_task(name="eroom.compute_leaderboard", bind=True, max_retries=2, default_retry_delay=60)
def compute_leaderboard(self, tag_id: str | None = None) -> dict:
    logger.info("Bắt đầu tính bảng xếp hạng (Celery)", extra={"tag_id": tag_id})
    try:
        week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
        with DBSession(engine) as session:
            rows = _fetch_week_leaderboard_data(session, week_start, tag_id)
            if not rows:
                return {"status": "completed", "entries": 0, "week_start": week_start}

            _delete_leaderboard_week(session, week_start, tag_id)
            entries = _insert_leaderboard_entries(session, rows, week_start, tag_id)
            session.commit()

        logger.info("Tính bảng xếp hạng hoàn tất (Celery)", extra={"entries": entries, "week_start": week_start})
        return {"status": "completed", "entries": entries, "week_start": week_start}
    except Exception as e:
        logger.error("Tính bảng xếp hạng thất bại (Celery)", exc_info=True)
        raise self.retry(exc=e)


def _fetch_week_leaderboard_data(
    session: DBSession, week_start: str, tag_id: str | None
) -> list:
    base_query = """
        SELECT
            s.user_id,
            s.tags,
            SUM(COALESCE(s.speaking_time_seconds, 0)) as total_speaking,
            AVG(COALESCE(s.avg_score, 0)) as avg_score,
            COUNT(DISTINCT s.id) as session_count
        FROM sessions s
        WHERE s.created_at >= :week_start
    """
    params: dict = {"week_start": week_start + " 00:00:00"}
    if tag_id:
        base_query += " AND s.tags LIKE :tag_pattern"
        params["tag_pattern"] = f"%{tag_id}%"

    base_query += " GROUP BY s.user_id, s.tags ORDER BY total_speaking DESC, avg_score DESC"
    return list(session.exec(text(base_query), params).all())


def _delete_leaderboard_week(session: DBSession, week_start: str, tag_id: str | None) -> None:
    delete_query = "DELETE FROM leaderboard WHERE week_start = :ws"
    delete_params: dict = {"ws": week_start}
    if tag_id:
        delete_query += " AND tag_id = :tid"
        delete_params["tid"] = tag_id
    session.exec(text(delete_query), delete_params)


def _insert_leaderboard_entries(
    session: DBSession, rows: list, week_start: str, tag_id: str | None
) -> int:
    entries = 0
    for rank, row in enumerate(rows, 1):
        row_tags = row.tags if row.tags else ""
        row_tag_id = tag_id or (
            row_tags.split(",")[0].strip() if "," in row_tags else row_tags.strip()
        )
        if not row_tag_id:
            continue
        session.exec(
            text(
                "INSERT INTO leaderboard (id, user_id, tag_id, week_start, speaking_time_seconds, "
                "avg_score, sessions_count, rank, created_at, updated_at) "
                "VALUES (:id, :uid, :tid, :ws, :st, :sc, :sn, :rk, NOW(), NOW())"
            ),
            {
                "id": str(uuid4()),
                "uid": row.user_id,
                "tid": row_tag_id,
                "ws": week_start,
                "st": int(row.total_speaking or 0),
                "sc": float(row.avg_score or 0),
                "sn": row.session_count or 0,
                "rk": rank,
            },
        )
        entries += 1
    return entries


@shared_task(name="eroom.cleanup_expired_rooms", bind=True, max_retries=1, default_retry_delay=10)
def cleanup_expired_rooms(self) -> int:
    cleaned = 0
    try:
        with Session(engine) as session:
            expired = session.exec(
                text(
                    "UPDATE rooms SET status = 'ARCHIVED' "
                    "WHERE status = 'ACTIVE' AND current_participants = 0 "
                    "AND updated_at < NOW() - INTERVAL 1 HOUR"
                )
            )
            cleaned = expired.rowcount if hasattr(expired, "rowcount") else 0
            session.commit()
        logger.info("Dọn phòng hết hạn hoàn tất (Celery)", extra={"cleaned": cleaned})
    except Exception as e:
        logger.error("Dọn phòng thất bại (Celery)", exc_info=True)
        raise self.retry(exc=e)
    return cleaned


@shared_task(name="eroom.cleanup_expired_tokens", bind=True, max_retries=1, default_retry_delay=10)
def cleanup_expired_tokens(self) -> int:
    cleaned = 0
    try:
        with Session(engine) as session:
            expired = session.exec(
                text("DELETE FROM refresh_tokens WHERE expires_at < NOW()")
            )
            cleaned = expired.rowcount if hasattr(expired, "rowcount") else 0
            session.commit()
        logger.info("Dọn token hết hạn hoàn tất (Celery)", extra={"cleaned": cleaned})
    except Exception as e:
        logger.error("Dọn token thất bại (Celery)", exc_info=True)
        raise self.retry(exc=e)
    return cleaned


@shared_task(name="eroom.room_heartbeat_tick", bind=True, max_retries=2, default_retry_delay=30)
def room_heartbeat_tick(self) -> int:
    count = 0
    try:
        from app.model.room import Room, RoomStatus
        with Session(engine) as session:
            active_rooms = session.exec(
                text("SELECT id, topic, tags FROM rooms WHERE status = :status AND current_participants > 0"),
                {"status": RoomStatus.ACTIVE.value},
            ).all()
            for row in active_rooms:
                tags = json.loads(row.tags) if isinstance(row.tags, str) and row.tags else []
                generate_heartbeat.delay(str(row.id), row.topic or "", tags)
                count += 1
            logger.info("Nhịp tim tick hoàn tất (Celery)", extra={"rooms": count})
    except Exception as e:
        logger.error("Nhịp tim tick thất bại (Celery)", exc_info=True)
    return count


def _publish_result(channel: str, room_id: str, user_id: str, data: dict) -> None:
    try:
        client = get_redis_client()
        payload = {"room_id": room_id, "user_id": user_id}
        payload.update(data)
        payload["room_id"] = room_id
        payload["user_id"] = user_id
        client.publish(channel, json.dumps(payload, default=str))
    except Exception:
        logger.error("Đăng kết quả lên Redis thất bại (Celery)", extra={"channel": channel, "room_id": room_id})
