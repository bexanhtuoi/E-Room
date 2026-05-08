from __future__ import annotations


def schedule_memory_summary(conversation_id: str) -> None:
    _ = conversation_id


def load_rag_knowledge(tag_ids: list[str], room_id: str) -> dict[str, object]:
    return {"room_id": room_id, "tag_ids": tag_ids, "status": "queued"}


def generate_session_note(session_id: str, user_id: str) -> dict[str, str]:
    return {"session_id": session_id, "user_id": user_id, "status": "queued"}
