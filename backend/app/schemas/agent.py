from __future__ import annotations

from pydantic import BaseModel

from app.model.common import AgentLevel


class AgentSelection(BaseModel):
    name: str
    mode: str = "auto"


class AgentStatusResponse(BaseModel):
    room_id: str
    level: AgentLevel
    heartbeat_quota: int
    expert_enabled: bool
    tts_enabled: bool
