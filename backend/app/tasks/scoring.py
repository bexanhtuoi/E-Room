from typing import Any, Dict, Optional

from sqlmodel import Session

from app.config import settings
from app.database import engine
from app.integration.celery import celery_app
from app.integration.scorer_client import score_remote
from app.log import get_logger
from app.repositories import pronunciation_score_crud, room_crud, session_crud
from app.shared.exceptions import ScorerUnavailableError

log = get_logger("app.tasks", level="INFO")


def score_with_backend(
    audio_path=None,
    reference_text: str = "",
    language: str = "en",
    confidence: float = 1.0,
    avg_logprob: float = 0.0,
    duration: float = 0.0,
    words=None,
):
    from app.ai.pronunciation import score_pronunciation

    backend = (settings.scorer_backend or "local").lower().replace("lambda", "remote")

    if backend in ("remote", "remote-strict") and audio_path:
        try:
            with open(audio_path, "rb") as handle:
                audio_bytes = handle.read()

            return score_remote(
                audio_bytes,
                reference_text,
                language=language,
                confidence=confidence,
                avg_logprob=avg_logprob,
                duration=duration,
                words=words,
            )
        except ScorerUnavailableError as error:
            if backend == "remote-strict":
                raise

            log.warning("Scorer remote loi, rot ve local | err=%s", error)

    return score_pronunciation(
        audio_path=audio_path,
        reference_text=reference_text,
        language=language,
        confidence=confidence,
        avg_logprob=avg_logprob,
        duration=duration,
        words=words,
    )


def score_room_utterance(
    db: Session,
    room_id: int,
    user_id: Any,
    message_id: Any,
    session_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    from app.ai.stt.audio_store import fetch_audio_bytes, is_s3_ref, materialize_temp_wav
    from app.ai.stt.recorder import find_attempt_by_message
    from app.ai.stt.speech_log import attach_pronunciation, read_user_log, resolve_audio_path

    if message_id is None:
        return None

    entries = read_user_log(room_id, user_id)
    entry = next((e for e in entries if e.get("message_id") == message_id), None)
    if entry is None:
        return None

    reference = (entry.get("corrected_text") or entry.get("text") or "").strip()
    if not reference:
        return None

    try:
        attempt = find_attempt_by_message(room_id, user_id, message_id)
    except Exception:
        attempt = None

    import os

    audio_path = None
    attempt_id: Any = None
    temp_paths: list = []
    if attempt and (attempt.get("raw_path") is not None or attempt.get("raw_object")):
        by_id = {e.get("message_id"): e for e in entries}
        parts = [
            (by_id[mid].get("corrected_text") or by_id[mid].get("text", ""))
            for mid in attempt.get("message_ids", [])
            if mid in by_id and (by_id[mid].get("corrected_text") or by_id[mid].get("text", "")).strip()
        ]
        if parts:
            if attempt.get("raw_path") is not None:
                audio_path = attempt["raw_path"]
            else:
                raw_bytes = fetch_audio_bytes(room_id, attempt.get("raw_object"))
                if raw_bytes is not None:
                    audio_path = materialize_temp_wav(raw_bytes)
                    temp_paths.append(audio_path)
            if audio_path is not None:
                reference = " ".join(parts)
                attempt_id = attempt.get("attempt_id")
    if audio_path is None:
        audio_file = entry.get("audio_file")
        audio_path = resolve_audio_path(room_id, audio_file)
        if audio_path is None and is_s3_ref(audio_file):
            raw_bytes = fetch_audio_bytes(room_id, audio_file)
            if raw_bytes is not None:
                audio_path = materialize_temp_wav(raw_bytes)
                temp_paths.append(audio_path)

    try:
        score = score_with_backend(
            audio_path=audio_path,
            reference_text=reference,
            language=entry.get("language", "en"),
            confidence=entry.get("confidence", 1.0),
            avg_logprob=entry.get("avg_logprob", 0.0),
            duration=entry.get("duration", 0.0),
            words=entry.get("words", []),
        )
    finally:
        for temp_path in temp_paths:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    score["scored_text"] = reference
    if attempt_id is not None:
        score["attempt_id"] = attempt_id

    updated = attach_pronunciation(room_id, user_id, message_id, score)

    try:
        pronunciation_score_crud.upsert_score(
            db,
            room_id=room_id,
            user_id=user_id,
            message_id=message_id,
            session_id=session_id,
            score=score,
        )
    except Exception as error:
        log.warning("score DB write-through failed | room=%s msg=%s err=%s", room_id, message_id, error)

    return updated or {**entry, "pronunciation": score}


@celery_app.task(name="app.tasks.scoring.score_single_utterance")
def score_single_utterance(
    room_id: int,
    user_id: Any,
    message_id: Any,
    session_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    with Session(engine) as db:
        try:
            return score_room_utterance(db, room_id, user_id, message_id, session_id)
        except Exception:
            log.exception("Single scoring failed | room=%s msg=%s", room_id, message_id)
            return None


@celery_app.task(name="app.tasks.scoring.score_room_utterances")
def score_room_utterances(room_id: int) -> int:
    from app.ai.stt.speech_log import list_room_users, read_user_log

    try:
        raw_uids = list_room_users(room_id)
    except Exception as error:
        log.warning("Room scoring skipped, no speech logs | room_id=%s error=%s", room_id, error)
        return 0

    scored = 0
    with Session(engine) as db:
        if room_crud.get_one(db, id=room_id) is None:
            return 0

        for raw_uid in raw_uids:
            try:
                user_id = int(raw_uid)
            except (TypeError, ValueError):
                continue

            entries = read_user_log(room_id, raw_uid)
            pending = [
                e for e in entries
                if e.get("message_id") is not None
                and not e.get("pronunciation")
                and (e.get("corrected_text") or e.get("text") or "").strip()
            ]
            if not pending:
                continue

            latest = session_crud.get_latest(db, user_id=user_id, room_id=room_id)
            session_id = latest.id if latest else None

            for entry in pending:
                try:
                    updated = score_room_utterance(db, room_id, raw_uid, entry.get("message_id"), session_id)
                except Exception:
                    log.exception("Batch scoring failed | room=%s msg=%s", room_id, entry.get("message_id"))
                    continue
                if updated is not None:
                    scored += 1

    if scored:
        log.info("Room scored after call | room_id=%s utterances=%s", room_id, scored)
    return scored
