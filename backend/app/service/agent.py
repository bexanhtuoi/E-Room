from __future__ import annotations

from app.model import AgentLevel, Room, SubscriptionTier


class AgentPolicyService:
    def resolve_room_agent_level(self, room: Room, participant_tiers: list[SubscriptionTier]) -> AgentLevel:
        if SubscriptionTier.PRO_PLUS in participant_tiers:
            return AgentLevel.FULL
        if SubscriptionTier.PRO in participant_tiers:
            return AgentLevel.ADVANCED
        return room.agent_level

    def get_heartbeat_quota(self, agent_level: AgentLevel) -> int:
        quotas = {
            AgentLevel.BASIC: 1,
            AgentLevel.ADVANCED: 3,
            AgentLevel.FULL: 5,
        }
        return quotas[agent_level]

    def is_expert_enabled(self, agent_level: AgentLevel) -> bool:
        return agent_level in {AgentLevel.ADVANCED, AgentLevel.FULL}

    def is_tts_enabled(self, agent_level: AgentLevel) -> bool:
        return agent_level == AgentLevel.FULL
