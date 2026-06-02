from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from app.infrastructure.redis_client import RedisCRUD, get_redis_client

logger = logging.getLogger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._redis = RedisCRUD(get_redis_client())
        self._subscribers: dict[str, list[Callable[[dict], None]]] = {}

    def publish(self, channel: str, payload: dict[str, Any]) -> int:
        return self._redis.publish(channel, payload)

    def subscribe(self, channel: str, handler: Callable) -> None:
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(handler)

    def unsubscribe(self, channel: str, handler: Callable) -> None:
        if channel in self._subscribers:
            self._subscribers[channel] = [h for h in self._subscribers[channel] if h is not handler]

    async def start_listener(self, *channels: str) -> None:
        pubsub = self._redis.pubsub()
        pubsub.subscribe(*channels)
        try:
            while True:
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is None:
                    await asyncio.sleep(0.01)
                    continue
                channel = message["channel"]
                for handler in self._subscribers.get(channel, []):
                    try:
                        handler(message)
                    except Exception:
                        logger.exception("EventBus handler error channel=%s", channel)
        finally:
            pubsub.close()


event_bus = EventBus()
