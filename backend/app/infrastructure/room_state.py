from __future__ import annotations

from enum import Enum
from typing import Optional

from app.infrastructure.redis import RedisCRUD, get_redis_client


class RoomStatus(str, Enum):
    IDLE = "IDLE"
    MATCHING = "MATCHING"
    AGENT_LOADING = "AGENT_LOADING"
    ACTIVE = "ACTIVE"
    DEACTIVE = "DEACTIVE"
    REVIEW = "REVIEW"
    END = "END"


class AgentLevel(str, Enum):
    BASIC = "basic"
    ADVANCED = "advanced"
    FULL = "full"


DEFAULT_ROOM_TTL = 3600


class RoomStateManager:
    _PREFIX = "engconnect:room"

    def __init__(self) -> None:
        self._redis = RedisCRUD(get_redis_client())

    def _key(self, room_id: str) -> str:
        return f"{self._PREFIX}:{room_id}"

    def create(self, room_id: str, **fields: str) -> None:
        key = self._key(room_id)
        self._redis.hmset(key, {"status": RoomStatus.IDLE.value, **fields})
        self._redis.expire(key, DEFAULT_ROOM_TTL)

    def set_status(self, room_id: str, status: RoomStatus) -> None:
        self._redis.hset(self._key(room_id), "status", status.value)

    def get_status(self, room_id: str) -> Optional[RoomStatus]:
        raw = self._redis.hget(self._key(room_id), "status")
        return RoomStatus(raw) if raw else None

    def set_agent_level(self, room_id: str, level: AgentLevel) -> None:
        self._redis.hset(self._key(room_id), "agent_level", level.value)

    def get_agent_level(self, room_id: str) -> AgentLevel:
        raw = self._redis.hget(self._key(room_id), "agent_level")
        return AgentLevel(raw) if raw else AgentLevel.BASIC

    def set_participant_count(self, room_id: str, count: int) -> None:
        self._redis.hset(self._key(room_id), "participant_count", str(count))

    def get_participant_count(self, room_id: str) -> int:
        raw = self._redis.hget(self._key(room_id), "participant_count")
        return int(raw) if raw else 0

    def set_topic(self, room_id: str, topic: str) -> None:
        self._redis.hset(self._key(room_id), "topic", topic)

    def get_field(self, room_id: str, field: str) -> Optional[str]:
        return self._redis.hget(self._key(room_id), field)

    def get_all(self, room_id: str) -> dict[str, str]:
        return self._redis.hgetall(self._key(room_id))

    def delete(self, room_id: str) -> None:
        self._redis.delete(self._key(room_id))

    def exists(self, room_id: str) -> bool:
        return self._redis.exists(self._key(room_id)) > 0


room_state_manager = RoomStateManager()
