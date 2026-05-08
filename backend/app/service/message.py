from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from app.model import Message, MessageType
from app.service.base import CRUDRepository


class MessageService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = CRUDRepository(Message)

    def get_many(self):
        return self.repo.get_many(self.session)

    def list_messages(self) -> list[dict]:
        return [message.model_dump(mode="json") for message in self.repo.get_many(self.session)]

    def list_room_messages(self, room_id: UUID) -> list[Message]:
        statement = select(Message).where(Message.room_id == room_id)
        return list(self.session.exec(statement))

    def create_transcript_message(self, room_id: UUID, user_id: UUID | None, content: str) -> Message:
        message = Message(room_id=room_id, user_id=user_id, content=content, message_type=MessageType.TRANSCRIPT)
        self.session.add(message)
        self.session.commit()
        self.session.refresh(message)
        return message

    def save(self, obj):
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def list_all(self):
        return self.repo.get_many(self.session)
