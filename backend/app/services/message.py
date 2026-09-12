import json
from datetime import datetime, timedelta
from typing import List, Optional

from sqlmodel import Session, select

from app.database import engine
from app.log import get_logger
from app.models import Message, MessageRole, User
from app.services.base import CRUDRepository
from app.utils.datetime_utils import as_naive_utc, now_utc

log = get_logger("app.services.message")

DUPLICATE_TRANSCRIPT_SECONDS = 10


def is_recent_duplicate(db: Session, room_id: int, user_id: Optional[int], text: str) -> bool:
    cutoff = as_naive_utc(now_utc()) - timedelta(seconds=DUPLICATE_TRANSCRIPT_SECONDS)
    existing = db.exec(
        select(Message)
        .where(
            Message.room_id == room_id,
            Message.user_id == user_id,
            Message.text == text,
            Message.created_at >= cutoff,
        )
        .limit(1)
    ).first()
    return existing is not None


class MessageCrud(CRUDRepository):
    def __init__(self) -> None:
        super().__init__(model=Message)

    def get_message_times(
        self,
        db: Session,
        user_id: int,
        since: Optional[datetime] = None,
    ) -> List[datetime]:

        stmt = select(Message.created_at).where(Message.user_id == user_id)

        if since is not None:
            stmt = stmt.where(Message.created_at >= since)

        return list(db.exec(stmt).all())

    def save_transcript(
        self,
        room_id: int,
        user_identity: str,
        text: str,
        duration: float,
        confidence: float,
        avg_logprob: float,
        words_count: int,
        language: Optional[str] = None,
    ) -> tuple[Optional[int], Optional[int], str]:
        user_id: Optional[int] = None
        user_name = user_identity

        try:
            user_id = int(user_identity)
        except ValueError:
            pass

        with Session(engine) as db:
            if user_id:
                user_obj = db.exec(select(User).where(User.id == user_id)).first()
                if user_obj:
                    user_name = user_obj.full_name

            if is_recent_duplicate(db, room_id, user_id, text):
                log.info("Dropping duplicate transcript | room_id=%s user=%s text='%s'", room_id, user_identity, text[:80])
                return None, user_id, user_name

            meta_data = {
                "source": "speech_to_text",
                "language": language or "en",
                "duration": duration,
                "confidence": confidence,
                "avg_logprob": avg_logprob,
                "words_count": words_count,
            }

            message = self.create(
                db,
                obj_in={
                    "room_id": room_id,
                    "user_id": user_id,
                    "role": MessageRole.USER,
                    "text": text,
                    "meta_data": json.dumps(meta_data),
                },
            )
            return message.id, user_id, user_name


message_crud = MessageCrud()
