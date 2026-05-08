from __future__ import annotations

from app.model import AgentLevel, Room, RoomParticipant, RoomStatus, SubscriptionTier
from app.service.base import BaseService


class RoomService(BaseService[Room]):
    def list_active_rooms(self) -> list[Room]:
        return [room for room in self.list_all() if room.status == RoomStatus.ACTIVE]

    def create_matching_room(self, room: Room) -> Room:
        room.status = RoomStatus.MATCHING
        return self.save(room)

    def activate_room(self, room_id: str) -> Room | None:
        room = self.get_by_id(room_id)
        if room is None:
            return None
        room.status = RoomStatus.ACTIVE
        return self.save(room)

    def resolve_agent_level(self, participant_tiers: list[SubscriptionTier]) -> AgentLevel:
        if SubscriptionTier.PRO_PLUS in participant_tiers:
            return AgentLevel.FULL
        if SubscriptionTier.PRO in participant_tiers:
            return AgentLevel.ADVANCED
        return AgentLevel.BASIC


class RoomParticipantService(BaseService[RoomParticipant]):
    def list_room_participants(self, room_id: str) -> list[RoomParticipant]:
        return [participant for participant in self.list_all() if participant.room_id == room_id]

    def add_participant(self, participant: RoomParticipant) -> RoomParticipant:
        return self.save(participant)
