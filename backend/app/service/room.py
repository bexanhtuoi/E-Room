from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.model import AgentLevel, Room, RoomParticipant, RoomStatus, SubscriptionTier
from app.service.base import CRUDRepository


class RoomService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = CRUDRepository(Room)

    def get_by_id(self, id: UUID):
        return self.session.get(self.repo._model, id)

    def list_all(self):
        return self.repo.get_many(self.session)

    def list_active_rooms(self) -> list[Room]:
        statement = select(Room).where(Room.status == RoomStatus.ACTIVE)
        return list(self.session.exec(statement))

    def create_matching_room(self, room: Room) -> Room:
        room.status = RoomStatus.MATCHING
        self.session.add(room)
        self.session.commit()
        self.session.refresh(room)
        return room

    def resolve_agent_level(self, participant_tiers: list[SubscriptionTier]) -> AgentLevel:
        if SubscriptionTier.PRO_PLUS in participant_tiers:
            return AgentLevel.FULL
        if SubscriptionTier.PRO in participant_tiers:
            return AgentLevel.ADVANCED
        return AgentLevel.BASIC


class RoomParticipantService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = CRUDRepository(RoomParticipant)

    def get_by_id(self, id: UUID):
        return self.session.get(self.repo._model, id)

    def list_room_participants(self, room_id: UUID) -> list[RoomParticipant]:
        statement = select(RoomParticipant).where(RoomParticipant.room_id == room_id)
        return list(self.session.exec(statement))

    def add_participant(self, participant: RoomParticipant) -> RoomParticipant:
        self.session.add(participant)
        self.session.commit()
        self.session.refresh(participant)
        return participant
