from __future__ import annotations

import asyncio
import json

from app.infrastructure.redis_client import get_redis_client
from app.log import get_logger

logger = get_logger(__name__)


class CeleryBridge:
    def __init__(self) -> None:
        self._subscriber = get_redis_client().pubsub()
        self._pubsub_task: asyncio.Task | None = None
        self._callbacks: dict[str, list[callable]] = {}

    def subscribe(self, channel: str, callback: callable) -> None:
        self._callbacks.setdefault(channel, []).append(callback)

    async def start(self) -> None:
        logger.info("CeleryBridge đã khởi động")
        for channel in self._callbacks:
            self._subscriber.subscribe(channel)
        self._pubsub_task = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        if self._pubsub_task:
            self._pubsub_task.cancel()
        self._subscriber.close()
        logger.info("CeleryBridge đã dừng")

    async def _listen(self) -> None:
        loop = asyncio.get_running_loop()
        while True:
            try:
                message = await loop.run_in_executor(None, self._subscriber.get_message, True)
                if message and message["type"] == "message":
                    channel = message["channel"].decode() if isinstance(message["channel"], bytes) else message["channel"]
                    data = json.loads(message["data"])
                    logger.info("Chuyển tiếp từ Redis",
                        extra={"channel": channel, "room_id": data.get("room_id", "")})
                    for cb in self._callbacks.get(channel, []):
                        await cb(channel, data)
            except asyncio.CancelledError:
                break
            except Exception:
                pass


def _to_ws_payload(event_type: str, data: dict) -> dict:
    base = {
        "type": event_type,
        "user_id": data.get("user_id", ""),
        "room_id": data.get("room_id", ""),
    }
    if event_type == "correction":
        base.update({
            "original": data.get("original", ""),
            "corrected": data.get("corrected", ""),
            "explanation": data.get("explanation", ""),
            "pronunciation_feedback": data.get("pronunciation_feedback", ""),
            "errors": data.get("errors", []),
            "tts_text": data.get("tts_text", data.get("corrected", "")),
            "created_at": data.get("created_at", ""),
        })
    elif event_type == "transcript":
        base.update({
            "text": data.get("text", ""),
            "scores": data.get("scores", {}),
            "needs_remediation": data.get("needs_remediation", False),
            "words": data.get("words", []),
            "aligned_phonemes": data.get("aligned_phonemes", []),
        })
    elif event_type == "heartbeat":
        base.update({
            "question_id": data.get("question_id", ""),
            "question": data.get("question", ""),
        })
    return base


celery_bridge = CeleryBridge()
