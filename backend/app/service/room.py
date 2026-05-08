from __future__ import annotations

from sqlmodel import Session, select

from app.model import AgentLevel, Room, RoomParticipant, RoomStatus, SubscriptionTier
from app.service.base import BaseService


class RoomService(BaseService[Room]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, Room)

    def list_active_rooms(self) -> list[Room]:
        statement = select(Room).where(Room.status == RoomStatus.ACTIVE)
        return list(self.session.exec(statement))

    def create_matching_room(self, room: Room) -> Room:
        room.status = RoomStatus.MATCHING
        return self.save(room)

    def resolve_agent_level(self, participant_tiers: list[SubscriptionTier]) -> AgentLevel:
        if SubscriptionTier.PRO_PLUS in participant_tiers:
            return AgentLevel.FULL
        if SubscriptionTier.PRO in participant_tiers:
            return AgentLevel.ADVANCED
        return AgentLevel.BASIC


class RoomParticipantService(BaseService[RoomParticipant]):
    def __init__(self, session: Session) -> None:
        super().__init__(session, RoomParticipant)

    def list_room_participants(self, room_id: str) -> list[RoomParticipant]:
        statement = select(RoomParticipant).where(RoomParticipant.room_id == room_id)
        return list(self.session.exec(statement))

    def add_participant(self, participant: RoomParticipant) -> RoomParticipant:
        return self.save(participant)
