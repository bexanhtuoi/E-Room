from typing import Any, Dict, Optional

from sqlmodel import Session

from app.config import settings
from app.log import get_logger
from app.repositories.session import session_crud
from app.services.base import ServiceBase
from app.services.room import room_service
from app.shared.exceptions import (
    NoScoreReportError,
    NotAuthorizedError,
    NothingToScoreError,
    ScoringQueueError,
    UtteranceNotFoundError,
)

log = get_logger("app.services.speech")

__all__ = [
    "SpeechService",
    "speech_service",
]


class SpeechService(ServiceBase):
    def ensure_room_visible(self, db: Session, user, room_id: int):
        room = room_service.get_room_or_404(db, room_id)
        room_service.ensure_room_access(room, user)

        return room


    def ensure_scorable_target(self, db: Session, user, room_id: int, target_uid: Any) -> Any:
        if target_uid is not None and target_uid != user.id and user.role != "admin":
            room = room_service.get_room_or_404(db, room_id)

            if not room or room.host_id != user.id:
                raise NotAuthorizedError()

        return target_uid if target_uid is not None else user.id


    def list_my_utterances(self, db: Session, user, room_id: int) -> list:
        from app.ai.stt.speech_log import read_user_log

        self.ensure_room_visible(db, user, room_id)

        return read_user_log(room_id, user.id)


    def list_room_utterances(self, db: Session, user, room_id: int) -> dict:
        from app.ai.stt.speech_log import read_room_logs

        self.ensure_room_visible(db, user, room_id)

        return read_room_logs(room_id)


    def room_summary_lines(self, db: Session, user, room_id: int) -> list:
        from app.ai.stt.speech_log import get_room_transcript_for_summary

        self.ensure_room_visible(db, user, room_id)

        return get_room_transcript_for_summary(room_id)


    def edit_utterance(self, db: Session, user, room_id: int, message_id: int, corrected_text: str) -> dict:
        from app.ai.stt.speech_log import update_corrected_text

        self.ensure_room_visible(db, user, room_id)

        updated = update_corrected_text(room_id, user.id, message_id, corrected_text)

        if updated is None:
            # Cho host/admin sửa hộ? V1 chỉ cho sửa câu của chính mình.
            raise UtteranceNotFoundError()

        return updated


    def find_utterance_entry(self, db: Session, user, room_id: int, target_uid: Any, message_id: int) -> dict:
        from app.ai.stt.speech_log import read_user_log

        self.ensure_room_visible(db, user, room_id)

        entries = read_user_log(room_id, target_uid)
        entry = next((item for item in entries if item.get("message_id") == message_id), None)

        if entry is None:
            raise UtteranceNotFoundError()

        return entry


    def utterance_needs_heavy_scoring(self, room_id: int, user_id: Any, message_id: Any, entry: Dict[str, Any]) -> bool:
        if settings.pronun_base_url:
            return False

        try:
            from app.ai.stt.recorder import find_attempt_by_message

            attempt = find_attempt_by_message(room_id, user_id, message_id)
            if attempt and attempt.get("raw_path") is not None:
                return True
        except Exception:
            pass

        try:
            from app.ai.stt.speech_log import resolve_audio_path

            return resolve_audio_path(room_id, entry.get("audio_file")) is not None
        except Exception:
            return False


    def score_utterance(self,
        db: Session, user, room_id: int, message_id: int, target_uid: Optional[int] = None,
    ) -> Dict[str, Any]:
        from app.tasks.scoring import score_room_utterance, score_single_utterance

        room = room_service.get_room_or_404(db, room_id)
        room_service.ensure_room_access(room, user)

        resolved_uid = self.ensure_scorable_target(db, user, room_id, target_uid)
        entry = self.find_utterance_entry(db, user, room_id, resolved_uid, message_id)
        open_session = session_crud.get_open(db, user_id=resolved_uid, room_id=room_id)

        if self.utterance_needs_heavy_scoring(room_id, resolved_uid, message_id, entry):
            try:
                score_single_utterance.apply_async(
                    args=[room_id, resolved_uid, message_id, open_session.id if open_session else None],
                    queue=settings.ai_queue_name,
                )
            except Exception as error:
                raise ScoringQueueError(detail=f"Hàng đợi chấm điểm không khả dụng: {error}")

            return {"queued": True, "room_id": room_id, "message_id": message_id}

        updated = score_room_utterance(
            db,
            room_id,
            resolved_uid,
            message_id,
            open_session.id if open_session else None,
        )

        if updated is None:
            raise NothingToScoreError()

        return updated


    def feedback_utterance(self,
        db: Session,
        user,
        room_id: int,
        message_id: int,
        target_uid: Optional[int] = None,
        model: str = "",
        temperature: float = 0.6,
        max_tokens: int = 2000,
    ) -> Dict[str, Any]:
        from app.ai.pronunciation import request_pronun_feedback
        from app.ai.stt.speech_log import attach_feedback
        from app.repositories.pronunciation_score import pronunciation_score_crud

        room = room_service.get_room_or_404(db, room_id)
        room_service.ensure_room_access(room, user)

        resolved_uid = self.ensure_scorable_target(db, user, room_id, target_uid)
        entry = self.find_utterance_entry(db, user, room_id, resolved_uid, message_id)

        report = (entry.get("pronunciation") or {}).get("report")

        if not report:
            raise NoScoreReportError()

        # request_pronun_feedback không raise khi LLM chết (trả fallback
        # rule-based từ word_details/top_errors) nên luôn 200 khi đã có report.
        feedback = request_pronun_feedback(
            scoring_report=report,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        updated = attach_feedback(room_id, resolved_uid, message_id, feedback)

        # Write-through feedback vào DB (khớp dòng điểm đã lưu ở POST .../score).
        try:
            row = pronunciation_score_crud.find_for_utterance(db, room_id, resolved_uid, message_id)

            if row is not None:
                pronunciation_score_crud.attach_feedback(db, row, feedback)
        except Exception as error:
            log.warning("feedback DB write-through failed | room=%s msg=%s err=%s", room_id, message_id, error)

        return updated or {**entry, "feedback": feedback}


speech_service = SpeechService()
