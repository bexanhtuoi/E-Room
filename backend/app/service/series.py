from __future__ import annotations

from app.model import LeaderboardEntry, RoomSeries, TopicRoom, TopicRoomRegistration
from app.service.base import CRUDRepository


class RoomSeriesService(CRUDRepository):
    def __init__(self, session) -> None:
        self.session = session
        super().__init__(RoomSeries)

    def list_all(self) -> list[RoomSeries]:
        return self.get_many(self.session)

    def list_series_by_tag(self, tag_id: str) -> list[RoomSeries]:
        return [
            series
            for series in self.get_many(self.session)
            if series.tag_id == tag_id
        ]

    def get_by_id(self, id) -> RoomSeries | None:
        return self.get_one(self.session, id=id)


class TopicRoomService(CRUDRepository):
    def __init__(self, session) -> None:
        self.session = session
        super().__init__(TopicRoom)

    def list_all(self) -> list[TopicRoom]:
        return self.get_many(self.session)

    def list_upcoming_rooms(
        self, tag_id: str | None = None
    ) -> list[TopicRoom]:
        rooms = self.get_many(self.session)
        if tag_id is None:
            return rooms
        return [room for room in rooms if room.tag_id == tag_id]

    def get_by_id(self, id) -> TopicRoom | None:
        return self.get_one(self.session, id=id)


class TopicRoomRegistrationService(CRUDRepository):
    def __init__(self, session) -> None:
        self.session = session
        super().__init__(TopicRoomRegistration)

    def list_all(self) -> list[TopicRoomRegistration]:
        return self.get_many(self.session)

    def list_registrations(
        self, topic_room_id: str
    ) -> list[TopicRoomRegistration]:
        return [
            reg
            for reg in self.get_many(self.session)
            if reg.topic_room_id == topic_room_id
        ]


class LeaderboardService(CRUDRepository):
    def __init__(self, session) -> None:
        self.session = session
        super().__init__(LeaderboardEntry)

    def list_all(self) -> list[LeaderboardEntry]:
        return self.get_many(self.session)

    def list_by_tag(self, tag_id: str) -> list[LeaderboardEntry]:
        return [
            entry
            for entry in self.get_many(self.session)
            if entry.tag_id == tag_id
        ]
