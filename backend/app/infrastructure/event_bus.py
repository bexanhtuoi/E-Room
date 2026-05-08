from __future__ import annotations

import json
from typing import Any

from app.infrastructure.redis import get_redis_client


class RoomEventBus:
    def __init__(self) -> None:
        self.redis = get_redis_client()

    def publish(self, room_id: str, payload: dict[str, Any]) -> None:
        self.redis.publish(f"e-room:room-events:{room_id}", json.dumps(payload))


event_bus = RoomEventBus()
