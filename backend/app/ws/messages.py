from __future__ import annotations

import json

from fastapi import WebSocket
from sqlmodel import Session

from app.agent.expert import answer_expert as ask_expert
from app.agent.heartbeat import generate_heartbeat_question
from app.database import engine
from app.log import get_logger
from app.model import Message, MessageType, Room, User
from app.ws.auth import now

log = get_logger(__name__)


def save_message(
    room_id: str,
    user_id: str | None,
    text: str,
    msg_type: str = MessageType.TEXT,
    sender_name: str = "",
    extra_payload: dict | None = None,
) -> Message | None:
    try:
        with Session(engine) as session:
            msg = Message(
                room_id=room_id,
                user_id=user_id,
                text=text,
                msg_type=msg_type,
                sender_name=sender_name,
                payload=extra_payload or {},
            )
            session.add(msg)
            session.commit()
            session.refresh(msg)
            return msg
    except Exception:
        log.warning("Lưu tin nhắn thất bại", exc_info=True)
        return None


async def generate_expert_reply(
    ws: WebSocket,
    room_id: str,
    user_id: str,
    question: str,
) -> None:
    try:
        await ask_expert(ws, room_id, user_id, question)
    except Exception:
        log.warning("Phản hồi chuyên gia thất bại", exc_info=True)
