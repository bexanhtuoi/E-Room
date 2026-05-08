from __future__ import annotations

from app.model import AgentMisuseLog, ModerationEvent
from app.service.base import BaseService


class ModerationEventService(BaseService[ModerationEvent]):
    def list_events_for_user(self, user_id: str) -> list[ModerationEvent]:
        return [event for event in self.list_all() if event.user_id == user_id]


class AgentMisuseService(BaseService[AgentMisuseLog]):
    def list_logs_for_user(self, user_id: str) -> list[AgentMisuseLog]:
        return [log for log in self.list_all() if log.user_id == user_id]

    def count_room_declines(self, room_id: str, user_id: str) -> int:
        return len([
            log
            for log in self.list_all()
            if log.room_id == room_id and log.user_id == user_id and log.action == "declined"
        ])
