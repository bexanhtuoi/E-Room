from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from app.model.common import AgentLevel, EnglishLevel, SubscriptionTier, RoomStatus
from app.model.subscription import Subscription, SubscriptionStatus


class TestSubscriptionTierOrdering:
    def test_free_is_lowest(self):
        tiers = sorted([SubscriptionTier.PRO, SubscriptionTier.FREE, SubscriptionTier.PRO_PLUS])
        assert tiers[0] == SubscriptionTier.FREE

    def test_pro_plus_is_highest(self):
        tiers = sorted([SubscriptionTier.PRO, SubscriptionTier.FREE, SubscriptionTier.PRO_PLUS])
        assert tiers[-1] == SubscriptionTier.PRO_PLUS

    def test_three_tiers_distinct(self):
        assert len({SubscriptionTier.FREE, SubscriptionTier.PRO, SubscriptionTier.PRO_PLUS}) == 3


class TestAgentLevelOrdering:
    def test_basic_lowest(self):
        levels = sorted([AgentLevel.FULL, AgentLevel.BASIC, AgentLevel.ADVANCED])
        assert levels[0] == AgentLevel.BASIC
        assert levels[-1] == AgentLevel.FULL


class TestRoomStatusFlow:
    def test_all_statuses_defined(self):
        expected = {"IDLE", "MATCHING", "AGENT_LOADING", "ACTIVE", "DEACTIVE", "REVIEW", "END"}
        actual = {s.value for s in RoomStatus}
        assert expected == actual

    def test_status_is_str_enum(self):
        assert isinstance(RoomStatus.ACTIVE, str)
        assert RoomStatus.ACTIVE == "ACTIVE"


class TestEnglishLevelOrder:
    def test_levels_ordered(self):
        levels = list(EnglishLevel)
        assert levels[0] == EnglishLevel.A1
        assert levels[-1] == EnglishLevel.C2

    def test_six_levels(self):
        assert len(list(EnglishLevel)) == 6


class TestSubscriptionModelDefaults:
    def test_default_tier_is_free(self):
        sub = Subscription()
        assert sub.tier == SubscriptionTier.FREE

    def test_default_status_is_active(self):
        sub = Subscription()
        assert sub.status == SubscriptionStatus.ACTIVE

    def test_all_statuses_defined(self):
        expected = {"active", "canceled", "past_due", "trialing"}
        actual = {s.value for s in SubscriptionStatus}
        assert expected == actual


class TestObsidianSubscriptionTableMatch:
    """Cross-reference: ERoom overview.md subscription table."""

    def test_free_quota_obsidian_match(self):
        """Free tier: corrections=3, heartbeat=1, expert=no, tts=no."""
        from app.service.agent import AgentPolicyService
        svc = AgentPolicyService()
        assert svc.is_expert_enabled(AgentLevel.BASIC) is False
        assert svc.is_tts_enabled(AgentLevel.BASIC) is False
        assert svc.get_heartbeat_quota(AgentLevel.BASIC) == 1

    def test_pro_quota_obsidian_match(self):
        """Pro tier: heartbeat=3, expert=yes (Web Search only), tts=no."""
        from app.service.agent import AgentPolicyService
        svc = AgentPolicyService()
        assert svc.is_expert_enabled(AgentLevel.ADVANCED) is True
        assert svc.is_tts_enabled(AgentLevel.ADVANCED) is False
        assert svc.get_heartbeat_quota(AgentLevel.ADVANCED) == 3

    def test_pro_plus_quota_obsidian_match(self):
        """Pro+ tier: heartbeat=5, expert=yes (RAG+Web), tts=yes."""
        from app.service.agent import AgentPolicyService
        svc = AgentPolicyService()
        assert svc.is_expert_enabled(AgentLevel.FULL) is True
        assert svc.is_tts_enabled(AgentLevel.FULL) is True
        assert svc.get_heartbeat_quota(AgentLevel.FULL) == 5
