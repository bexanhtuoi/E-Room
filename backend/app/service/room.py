from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from app.model import AgentLevel, Room, RoomParticipant, RoomStatus, SubscriptionTier
from app.service.base import CRUDRepository


class RoomService(CRUDRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        super().__init__(Room)

    def get_by_id(self, id: UUID) -> Room | None:
        return self.get_one(self.session, id=id)

    def list_all(self) -> list[Room]:
        return self.get_many(self.session)

    def list_active_rooms(self) -> list[Room]:
        return self.get_many(self.session, status=RoomStatus.ACTIVE)

    def create_matching_room(self, room: Room) -> Room:
        room.status = RoomStatus.MATCHING
        self.session.add(room)
        self.session.commit()
        self.session.refresh(room)
        return room

    @staticmethod
    def resolve_agent_level(
        participant_tiers: list[SubscriptionTier],
    ) -> AgentLevel:
        if SubscriptionTier.PRO_PLUS in participant_tiers:
            return AgentLevel.FULL
        if SubscriptionTier.PRO in participant_tiers:
            return AgentLevel.ADVANCED
        return AgentLevel.BASIC

    def save(self, obj: Room) -> Room:
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj


class RoomParticipantService(CRUDRepository):
    def __init__(self, session: Session) -> None:
        self.session = session
        super().__init__(RoomParticipant)

    def get_by_id(self, id: UUID) -> RoomParticipant | None:
        return self.get_one(self.session, id=id)

    def list_room_participants(self, room_id: UUID) -> list[RoomParticipant]:
        return self.get_many(self.session, room_id=room_id)

    def get_room_participant(self, room_id: UUID, user_id: UUID) -> RoomParticipant | None:
        return self.get_one(self.session, room_id=room_id, user_id=user_id)

    def add_participant(
        self, participant: RoomParticipant
    ) -> RoomParticipant:
        self.session.add(participant)
        self.session.commit()
        self.session.refresh(participant)
        return participant
