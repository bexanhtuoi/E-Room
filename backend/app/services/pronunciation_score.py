import json
from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from app.models.pronunciation_score import PronunciationScore
from app.services.base import CRUDRepository
from app.utils.datetime_utils import now_utc


class PronunciationScoreCrud(CRUDRepository):
    def __init__(self) -> None:
        super().__init__(model=PronunciationScore)

    def find_for_utterance(
        self, db: Session, room_id: int, user_id: int, message_id: Any
    ) -> Optional[PronunciationScore]:
        """Tìm dòng điểm của 1 câu. message_id None (log cũ) -> None để
        caller insert dòng mới thay vì upsert sai."""
        if message_id is None:
            return None
        stmt = (
            select(PronunciationScore)
            .where(PronunciationScore.room_id == room_id)
            .where(PronunciationScore.user_id == user_id)
            .where(PronunciationScore.message_id == message_id)
            .order_by(PronunciationScore.id.desc())
        )
        return db.exec(stmt).first()

    def upsert_score(
        self,
        db: Session,
        room_id: int,
        user_id: int,
        message_id: Any,
        session_id: Any,
        score: Dict[str, Any],
    ) -> PronunciationScore:
        """Write-through sau POST .../score: chấm lại thì UPDATE (không đẻ dòng mới)."""
        details = score.get("details") or {}
        report = score.get("report") or {}
        scores = report.get("scores") or {}
        payload = {
            "room_id": room_id,
            "user_id": user_id,
            "message_id": message_id,
            "session_id": session_id,
            "scored_text": score.get("scored_text", ""),
            "overall": float(scores.get("overall", score.get("score", 0.0) or 0.0)),
            "sounds": float(scores.get("sounds", details.get("sounds", 0.0) or 0.0)),
            "stress": float(scores.get("stress", details.get("stress", 0.0) or 0.0)),
            "fluency": float(scores.get("fluency", details.get("fluency", 0.0) or 0.0)),
            "completeness": float(scores.get("completeness", details.get("completeness", 0.0) or 0.0)),
            "method": str(score.get("method", "")),
            "scorer_version": str(report.get("scorer_version", score.get("scorer_version", ""))),
            "report_json": json.dumps(report, ensure_ascii=False),
            "updated_at": now_utc(),
        }
        existing = self.find_for_utterance(db, room_id, user_id, message_id)
        if existing is None:
            # Sửa text rồi chấm lại (message_id mới hoặc log cũ) -> dòng mới.
            return self.create(db, obj_in={**payload, "feedback_json": None})
        payload.pop("message_id", None)
        # Chấm lại cùng câu: reset feedback cũ (khớp luật JSONL reset về None).
        return self.update(db, existing, obj_in={**payload, "feedback_json": None})

    def attach_feedback(
        self, db: Session, row: PronunciationScore, feedback: Dict[str, Any]
    ) -> PronunciationScore:
        return self.update(
            db, row, obj_in={"feedback_json": json.dumps(feedback, ensure_ascii=False), "updated_at": now_utc()}
        )

    def scored_in_window(
        self, db: Session, room_id: int, user_id: int, start, end=None
    ) -> List[PronunciationScore]:
        """Các dòng đã chấm của user trong khoảng session (DB là nguồn thật)."""
        stmt = (
            select(PronunciationScore)
            .where(PronunciationScore.room_id == room_id)
            .where(PronunciationScore.user_id == user_id)
            .where(PronunciationScore.created_at >= start)
            .order_by(PronunciationScore.id.asc())
        )
        if end is not None:
            stmt = stmt.where(PronunciationScore.created_at <= end)
        return list(db.exec(stmt).all())


pronunciation_score_crud = PronunciationScoreCrud()
