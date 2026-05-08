from __future__ import annotations

from app.model import Message, MessageType
from app.service.base import BaseService


class MessageService(BaseService[Message]):
    def list_messages(self) -> list[dict]:
        return [message.model_dump(mode="json") for message in self.list_all()]

    def list_room_messages(self, room_id: str) -> list[Message]:
        return [message for message in self.list_all() if message.room_id == room_id]

    def create_transcript_message(self, room_id: str, user_id: str, content: str) -> Message:
        message = Message(room_id=room_id, user_id=user_id, content=content, message_type=MessageType.TRANSCRIPT)
        return self.save(message)
