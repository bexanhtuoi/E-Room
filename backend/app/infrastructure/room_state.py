from __future__ import annotations

import json
from uuid import UUID

from app.infrastructure.redis_client import get_redis_client
from app.model.common import AgentLevel, RoomStatus


class RoomStateRepository:
    def __init__(self) -> None:
        self.redis = get_redis_client()

    def set_room_state(self, room_id: UUID, status: RoomStatus, agent_level: AgentLevel, participant_count: int) -> None:
        payload = {
            "status": status,
            "agentLevel": agent_level,
            "participantCount": participant_count,
        }
        self.redis.set(f"e-room:room:{room_id}", json.dumps(payload))

    def enqueue_user_for_tag(self, tag_slug: str, user_id: UUID, timestamp: float) -> None:
        self.redis.zadd(f"e-room:queue:tag:{tag_slug}", {str(user_id): timestamp})

    def get_room_state(self, room_id: UUID) -> dict[str, object] | None:
        raw = self.redis.get(f"e-room:room:{room_id}")
        if raw is None:
            return None
        return json.loads(raw)
