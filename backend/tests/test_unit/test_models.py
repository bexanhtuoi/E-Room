from __future__ import annotations

import pytest
from uuid import UUID, uuid4
from sqlmodel import SQLModel

from app.model.common import EnglishLevel, SubscriptionTier, AgentLevel, RoomStatus, MessageType
from app.model.user import User, UserBase
from app.model.room import Room, RoomBase, RoomParticipant
from app.model.tag import Tag, TagBase


class TestEnglishLevel:
    def test_all_values(self):
        assert EnglishLevel.A1 == "A1"
        assert EnglishLevel.A2 == "A2"
        assert EnglishLevel.B1 == "B1"
        assert EnglishLevel.B2 == "B2"
        assert EnglishLevel.C1 == "C1"
        assert EnglishLevel.C2 == "C2"

    def test_comparison(self):
        levels = list(EnglishLevel)
        assert levels[0] == EnglishLevel.A1
        assert levels[5] == EnglishLevel.C2


class TestRoomStatus:
    def test_all_states(self):
        states = {s.value for s in RoomStatus}
        assert "IDLE" in states
        assert "MATCHING" in states
        assert "AGENT_LOADING" in states
        assert "ACTIVE" in states
        assert "DEACTIVE" in states
        assert "REVIEW" in states
        assert "END" in states

    def test_count(self):
        assert len(list(RoomStatus)) == 7


class TestSubscriptionTier:
    def test_values(self):
        assert SubscriptionTier.FREE == "free"
        assert SubscriptionTier.PRO == "pro"
        assert SubscriptionTier.PRO_PLUS == "pro_plus"


class TestAgentLevel:
    def test_values(self):
        assert AgentLevel.BASIC == "basic"
        assert AgentLevel.ADVANCED == "advanced"
        assert AgentLevel.FULL == "full"


class TestMessageType:
    def test_all_types(self):
        types = {m.value for m in MessageType}
        assert "text" in types
        assert "system" in types
        assert "transcript" in types
        assert "ai_correction" in types
        assert "ai_expert" in types
        assert "ai_heartbeat" in types
        assert "ai_review" in types
        assert "tts_audio" in types


class TestUserModel:
    def test_default_values(self):
        user = User(email="test@example.com", display_name="Test")
        assert user.auto_join_enabled is True
        assert user.profile_completed is False
        assert user.email_verified is False
        assert user.is_active is True
        assert user.is_banned is False
        assert user.strikes == 0

    def test_unique_email(self):
        assert User.__tablename__ == "users"

    def test_english_level_none_allowed(self):
        user = User(email="x@x.com", display_name="X")
        assert user.english_level is None

    def test_uuid_generated(self, db_session):
        user = User(email="uuid-test@test.com", display_name="UUID Test")
        db_session.add(user)
        db_session.commit()
        assert isinstance(user.id, UUID)
        assert len(str(user.id)) == 36


class TestRoomModel:
    def test_default_values(self):
        room = Room(livekit_room_name="test-room-1")
        assert room.status == RoomStatus.IDLE
        assert room.agent_level == AgentLevel.BASIC
        assert room.max_participants == 5
        assert room.current_participants == 0
        assert room.session_duration_seconds == 900
        assert room.is_private is False
        assert room.is_public is True

    def test_tags_default_empty(self):
        room = Room(livekit_room_name="test-room-2")
        assert room.tags == []

    def test_unique_room_name(self):
        assert Room.__tablename__ == "rooms"

    def test_field_constraints(self):
        room = Room(livekit_room_name="test-room-3")
        assert room.max_participants >= 3
        assert room.max_participants <= 5
        assert room.session_duration_seconds >= 300
        assert room.session_duration_seconds <= 3600


class TestRoomParticipant:
    def test_default_values(self):
        rp = RoomParticipant(room_id=uuid4(), user_id=uuid4())
        assert rp.speaking_time_seconds == 0
        assert rp.words_spoken == 0
        assert rp.is_muted is False
        assert rp.connection_quality is None


class TestModelTablenames:
    def test_tablenames_consistent(self):
        assert User.__tablename__ == "users"
        assert Room.__tablename__ == "rooms"
        assert RoomParticipant.__tablename__ == "room_participants"
