from __future__ import annotations

from app.model import LeaderboardEntry, RoomSeries, TopicRoom, TopicRoomRegistration
from app.service.base import BaseService


class RoomSeriesService(BaseService[RoomSeries]):
    def list_series_by_tag(self, tag_id: str) -> list[RoomSeries]:
        return [series for series in self.list_all() if series.tag_id == tag_id]


class TopicRoomService(BaseService[TopicRoom]):
    def list_upcoming_rooms(self, tag_id: str | None = None) -> list[TopicRoom]:
        rooms = self.list_all()
        if tag_id is None:
            return rooms
        return [room for room in rooms if room.tag_id == tag_id]


class TopicRoomRegistrationService(BaseService[TopicRoomRegistration]):
    def list_registrations(self, topic_room_id: str) -> list[TopicRoomRegistration]:
        return [registration for registration in self.list_all() if registration.topic_room_id == topic_room_id]


class LeaderboardService(BaseService[LeaderboardEntry]):
    def list_by_tag(self, tag_id: str) -> list[LeaderboardEntry]:
        return [entry for entry in self.list_all() if entry.tag_id == tag_id]
