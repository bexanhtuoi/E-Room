from __future__ import annotations

from celery import shared_task
from sqlmodel import Session, select

from app.database import engine
from app.log import get_logger
from app.model.room import Room, RoomStatus

logger = get_logger(__name__)


@shared_task(name="eroom.run_matchmaking_tick", bind=True, max_retries=2, default_retry_delay=5)
def run_matchmaking_tick(self) -> int:
    matched_count = 0
    try:
        with Session(engine) as session:
            waiting_rooms = session.exec(
                select(Room).where(Room.status == RoomStatus.MATCHING)
            ).all()
            if len(waiting_rooms) < 2:
                return 0

            import itertools

            def _jaccard(a: set, b: set) -> float:
                if not a and not b:
                    return 1.0
                if not a or not b:
                    return 0.0
                return len(a & b) / len(a | b)

            def _extract_tags(room: Room) -> set[str]:
                tags: set[str] = set()
                if hasattr(room, "tags") and room.tags:
                    for t in room.tags:
                        tags.add(t.name.lower() if hasattr(t, "name") else str(t).lower())
                return tags

            for r1, r2 in itertools.combinations(waiting_rooms, 2):
                if r1.status != RoomStatus.MATCHING or r2.status != RoomStatus.MATCHING:
                    continue
                tags1 = _extract_tags(r1)
                tags2 = _extract_tags(r2)
                topic_sim = 1.0 if r1.topic and r2.topic and r1.topic.lower() == r2.topic.lower() else 0.0
                tag_sim = _jaccard(tags1, tags2)
                combined = 0.4 * topic_sim + 0.6 * tag_sim
                if combined > 0.3:
                    r1.status = RoomStatus.ACTIVE
                    r2.status = RoomStatus.ACTIVE
                    session.add_all([r1, r2])
                    matched_count += 2
            session.commit()
        logger.info("matchmaking_tick_done", extra={"matched": matched_count})
    except Exception as e:
        logger.error("matchmaking_tick_failed", exc_info=True)
        raise self.retry(exc=e)
    return matched_count
