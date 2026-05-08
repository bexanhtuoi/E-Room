from __future__ import annotations

from app.model import LeaderboardEntry, RoomSeries, TopicRoom, TopicRoomRegistration
from app.service.base import CRUDRepository


class RoomSeriesService:
    def __init__(self, session) -> None:
        self.session = session
        self.repo = CRUDRepository(RoomSeries)

    def list_all(self):
        return self.repo.get_many(self.session)

    def list_series_by_tag(self, tag_id: str) -> list[RoomSeries]:
        return [series for series in self.repo.get_many(self.session) if series.tag_id == tag_id]


class TopicRoomService:
    def __init__(self, session) -> None:
        self.session = session
        self.repo = CRUDRepository(TopicRoom)

    def list_all(self):
        return self.repo.get_many(self.session)

    def list_upcoming_rooms(self, tag_id: str | None = None) -> list[TopicRoom]:
        rooms = self.repo.get_many(self.session)
        if tag_id is None:
            return rooms
        return [room for room in rooms if room.tag_id == tag_id]


class TopicRoomRegistrationService:
    def __init__(self, session) -> None:
        self.session = session
        self.repo = CRUDRepository(TopicRoomRegistration)

    def list_all(self):
        return self.repo.get_many(self.session)

    def list_registrations(self, topic_room_id: str) -> list[TopicRoomRegistration]:
        return [registration for registration in self.repo.get_many(self.session) if registration.topic_room_id == topic_room_id]


class LeaderboardService:
    def __init__(self, session) -> None:
        self.session = session
        self.repo = CRUDRepository(LeaderboardEntry)

    def list_all(self):
        return self.repo.get_many(self.session)

    def list_by_tag(self, tag_id: str) -> list[LeaderboardEntry]:
        return [entry for entry in self.repo.get_many(self.session) if entry.tag_id == tag_id]
