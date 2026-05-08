from __future__ import annotations

from uuid import UUID

from sqlmodel import JSON, Column, Field, SQLModel

from app.model.common import MessageType, TimestampedModel


class MessageBase(SQLModel):
    room_id: UUID = Field(foreign_key="rooms.id", index=True)
    user_id: UUID | None = Field(default=None, foreign_key="users.id")
    content: str
    message_type: MessageType = MessageType.TEXT
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))


class Message(TimestampedModel, MessageBase, table=True):
    __tablename__ = "messages"
