from __future__ import annotations

import re

from celery import shared_task
from sqlmodel import Session, select

from app.database import engine
from app.log import get_logger
from app.model.room import Room, RoomStatus
from app.model.message import Message

logger = get_logger(__name__)

NSFW_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(fuck|shit|damn|asshole|bitch|bastard)\b", re.IGNORECASE),
    re.compile(r"(spam|scam|phish)\s*(link|url|site)", re.IGNORECASE),
    re.compile(r"(buy|sell|discount|offer)\s*(now|today|limited)", re.IGNORECASE),
]


@shared_task(name="eroom.scan_active_rooms", bind=True, max_retries=2, default_retry_delay=5)
def scan_active_rooms(self) -> dict:
    flagged_rooms: list[str] = []
    flagged_messages: int = 0
    try:
        with Session(engine) as session:
            active_rooms = session.exec(select(Room).where(Room.status == RoomStatus.ACTIVE)).all()
            for room in active_rooms:
                messages = session.exec(
                    select(Message).where(Message.room_id == room.id).order_by(Message.created_at.desc()).limit(20)
                ).all()
                room_flagged = False
                for msg in messages:
                    if not msg.content:
                        continue
                    for pattern in NSFW_PATTERNS:
                        if pattern.search(msg.content):
                            msg.is_flagged = True
                            session.add(msg)
                            flagged_messages += 1
                            room_flagged = True
                            break
                if room_flagged:
                    flagged_rooms.append(str(room.id))
            session.commit()
        logger.info("moderation_scan_done", extra={"flagged_rooms": len(flagged_rooms), "flagged_messages": flagged_messages})
    except Exception as e:
        logger.error("moderation_scan_failed", exc_info=True)
        raise self.retry(exc=e)
    return {"flagged_rooms": flagged_rooms, "flagged_messages": flagged_messages}
