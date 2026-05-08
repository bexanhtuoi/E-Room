from __future__ import annotations

from app.model import AgentMisuseLog, ModerationEvent
from app.service.base import CRUDRepository


class ModerationEventService:
    def __init__(self, session) -> None:
        self.session = session
        self.repo = CRUDRepository(ModerationEvent)

    def list_all(self):
        return self.repo.get_many(self.session)

    def list_events_for_user(self, user_id: str) -> list[ModerationEvent]:
        return [event for event in self.repo.get_many(self.session) if event.user_id == user_id]


class AgentMisuseService:
    def __init__(self, session) -> None:
        self.session = session
        self.repo = CRUDRepository(AgentMisuseLog)

    def list_all(self):
        return self.repo.get_many(self.session)

    def list_logs_for_user(self, user_id: str) -> list[AgentMisuseLog]:
        return [log for log in self.repo.get_many(self.session) if log.user_id == user_id]

    def count_room_declines(self, room_id: str, user_id: str) -> int:
        return len([
            log
            for log in self.repo.get_many(self.session)
            if log.room_id == room_id and log.user_id == user_id and log.action == "declined"
        ])
