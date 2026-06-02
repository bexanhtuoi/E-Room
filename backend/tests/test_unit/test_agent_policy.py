from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.model.common import AgentLevel, SubscriptionTier
from app.service.agent import AgentPolicyService


class TestResolveRoomAgentLevel:
    def test_pro_plus_gives_full(self):
        svc = AgentPolicyService()
        room = MagicMock()
        room.agent_level = AgentLevel.BASIC
        result = svc.resolve_room_agent_level(room, [SubscriptionTier.FREE, SubscriptionTier.PRO_PLUS])
        assert result == AgentLevel.FULL

    def test_pro_gives_advanced(self):
        svc = AgentPolicyService()
        room = MagicMock()
        room.agent_level = AgentLevel.BASIC
        result = svc.resolve_room_agent_level(room, [SubscriptionTier.FREE, SubscriptionTier.PRO])
        assert result == AgentLevel.ADVANCED

    def test_only_free_uses_room_level(self):
        svc = AgentPolicyService()
        room = MagicMock()
        room.agent_level = AgentLevel.BASIC
        result = svc.resolve_room_agent_level(room, [SubscriptionTier.FREE, SubscriptionTier.FREE])
        assert result == AgentLevel.BASIC

    def test_empty_participants_uses_room_level(self):
        svc = AgentPolicyService()
        room = MagicMock()
        room.agent_level = AgentLevel.FULL
        result = svc.resolve_room_agent_level(room, [])
        assert result == AgentLevel.FULL

    def test_pro_plus_overrides_pro(self):
        svc = AgentPolicyService()
        room = MagicMock()
        room.agent_level = AgentLevel.BASIC
        result = svc.resolve_room_agent_level(room, [SubscriptionTier.PRO, SubscriptionTier.PRO_PLUS])
        assert result == AgentLevel.FULL

    def test_single_pro_in_room_elevates_all(self):
        svc = AgentPolicyService()
        room = MagicMock()
        room.agent_level = AgentLevel.BASIC
        result = svc.resolve_room_agent_level(room, [
            SubscriptionTier.FREE, SubscriptionTier.FREE, SubscriptionTier.PRO
        ])
        assert result == AgentLevel.ADVANCED


class TestHeartbeatQuota:
    def test_basic_quota(self):
        svc = AgentPolicyService()
        assert svc.get_heartbeat_quota(AgentLevel.BASIC) == 1

    def test_advanced_quota(self):
        svc = AgentPolicyService()
        assert svc.get_heartbeat_quota(AgentLevel.ADVANCED) == 3

    def test_full_quota(self):
        svc = AgentPolicyService()
        assert svc.get_heartbeat_quota(AgentLevel.FULL) == 5


class TestExpertEnabled:
    def test_basic_no_expert(self):
        svc = AgentPolicyService()
        assert svc.is_expert_enabled(AgentLevel.BASIC) is False

    def test_advanced_has_expert(self):
        svc = AgentPolicyService()
        assert svc.is_expert_enabled(AgentLevel.ADVANCED) is True

    def test_full_has_expert(self):
        svc = AgentPolicyService()
        assert svc.is_expert_enabled(AgentLevel.FULL) is True


class TestTTSEnabled:
    def test_basic_no_tts(self):
        svc = AgentPolicyService()
        assert svc.is_tts_enabled(AgentLevel.BASIC) is False

    def test_advanced_no_tts(self):
        svc = AgentPolicyService()
        assert svc.is_tts_enabled(AgentLevel.ADVANCED) is False

    def test_full_has_tts(self):
        svc = AgentPolicyService()
        assert svc.is_tts_enabled(AgentLevel.FULL) is True


class TestCrossReferenceObsidianQuotas:
    """Verify quotas match ERoom Obsidian notes.md subscription table."""

    def test_basic_level_obsidian_match(self):
        """Obsidian: Basic → corrections=3, heartbeat=1, expert=no, tts=no."""
        svc = AgentPolicyService()
        assert svc.get_heartbeat_quota(AgentLevel.BASIC) == 1
        assert svc.is_expert_enabled(AgentLevel.BASIC) is False
        assert svc.is_tts_enabled(AgentLevel.BASIC) is False

    def test_advanced_level_obsidian_match(self):
        """Obsidian: Advanced → heartbeat=3, expert=yes, tts=no."""
        svc = AgentPolicyService()
        assert svc.get_heartbeat_quota(AgentLevel.ADVANCED) == 3
        assert svc.is_expert_enabled(AgentLevel.ADVANCED) is True
        assert svc.is_tts_enabled(AgentLevel.ADVANCED) is False

    def test_full_level_obsidian_match(self):
        """Obsidian: Full → heartbeat=5, expert=yes, tts=yes."""
        svc = AgentPolicyService()
        assert svc.get_heartbeat_quota(AgentLevel.FULL) == 5
        assert svc.is_expert_enabled(AgentLevel.FULL) is True
        assert svc.is_tts_enabled(AgentLevel.FULL) is True
