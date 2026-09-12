from typing import List

from app.models import DocumentKind


def build_room_context(room, skills: List) -> str:
    
    prompt = (getattr(room, "system_prompt", None) or "").strip() if room is not None else ""

    active_skills = [
        f"- {skill.file_name}: {(skill.content or '').strip()}"
        for skill in skills or []
        if getattr(skill, "kind", None) == DocumentKind.SKILL
        and getattr(skill, "enabled", False)
        and (skill.content or "").strip()
    ]

    has_docs = any(getattr(skill, "kind", None) == DocumentKind.FILE for skill in skills or [])

    if room is None or not (has_docs or prompt or active_skills):
        return ""

    parts = []
    if getattr(room, "name", None):
        parts.append(f"You are assisting in the room '{room.name}'.")

    if prompt:
        parts.append(f"Room instructions from the host (highest priority): {prompt}")

    if active_skills:
        parts.append("Enabled room skills (follow them):\n" + "\n".join(active_skills))

    parts.append(
        f"This room has a knowledge base. When you need facts, always call "
        f"retrieval_documents with tag='room:{room.id}' before answering from general knowledge."
    )

    return "\n".join(parts)
