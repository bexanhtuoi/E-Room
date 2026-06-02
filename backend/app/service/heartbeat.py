from __future__ import annotations

import asyncio
import json

from sqlmodel import Session, select

from app.agent.heartbeat import generate_heartbeat_question
from app.config import settings
from app.database import engine
from app.infrastructure.redis_client import get_redis_client
from app.log import get_logger
from app.model import Room, RoomParticipant

log = get_logger(__name__)


async def heartbeat_loop() -> None:
    while True:
        try:
            await asyncio.sleep(settings.heartbeat_interval_seconds)
            with Session(engine) as session:
                rooms = session.exec(
                    select(Room).where(Room.current_participants > 0)
                ).all()
            active_rooms = [r for r in rooms if r.current_participants > 0]
            log.info("Nhịp tim - kiểm tra phòng hoạt động",
                extra={"active_rooms": len(active_rooms)})

            for room in active_rooms:
                try:
                    topic = getattr(room, "topic", None) or "AI"
                    context = f"Phòng: {topic}. Hội thoại gần đây: "
                    log.info("Nhịp tim - gửi câu hỏi đến phòng",
                        extra={"room_id": room.id, "heartbeat_count": 0})

                    data = await generate_heartbeat_question(room.id, context)
                    if data and "question" in data:
                        client = get_redis_client()
                        client.publish(
                            "room:heartbeat",
                            json.dumps({
                                "room_id": room.id,
                                **data,
                            }, default=str),
                        )
                except Exception:
                    log.warning("Nhịp tim - gửi câu hỏi thất bại",
                        exc_info=True, extra={"room_id": room.id})
        except Exception:
            log.warning("Nhịp tim - lỗi vòng lặp", exc_info=True)
