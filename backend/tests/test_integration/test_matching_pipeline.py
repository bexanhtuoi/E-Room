from __future__ import annotations

import pytest
from sqlmodel import Session, select

from app.infrastructure.celery.matching import run_matchmaking_tick
from app.model.common import EnglishLevel, RoomStatus
from app.model.room import Room


@pytest.fixture(autouse=True)
def _patch_matching_engine(db_session):
    """Route matching tick to test DB instead of production engine."""
    import app.infrastructure.celery.matching as _mm
    _orig = _mm.engine
    _mm.engine = db_session.get_bind()
    yield
    _mm.engine = _orig


def _make_room(session: Session, name: str, topic: str | None = None,
               tags: list[str] | None = None,
               english_level: EnglishLevel | None = None,
               status: RoomStatus = RoomStatus.MATCHING) -> Room:
    room = Room(
        livekit_room_name=name,
        topic=topic,
        tags=tags or [],
        english_level=english_level,
        status=status,
    )
    session.add(room)
    session.commit()
    session.refresh(room)
    return room


class TestMatchingPipeline:
    """Integration tests for the matchmaking tick (Celery task)."""

    def test_empty_room_pool(self, db_session):
        """No MATCHING rooms → returns 0."""
        # Ensure no rooms in the test DB
        rooms = db_session.exec(select(Room)).all()
        for r in rooms:
            db_session.delete(r)
        db_session.commit()

        result = run_matchmaking_tick()
        assert result == 0

    def test_single_room_no_match(self, db_session):
        """One MATCHING room → no pair can be formed."""
        rooms = db_session.exec(select(Room)).all()
        for r in rooms:
            db_session.delete(r)
        db_session.commit()

        _make_room(db_session, "solo-room", topic="music", tags=["pop"])
        result = run_matchmaking_tick()
        assert result == 0
        # Room should still be MATCHING
        solo = db_session.exec(select(Room).where(Room.livekit_room_name == "solo-room")).one()
        assert solo.status == RoomStatus.MATCHING

    def test_perfect_match_pair(self, db_session):
        """Two rooms with identical topic, tags, English level → matched."""
        rooms = db_session.exec(select(Room)).all()
        for r in rooms:
            db_session.delete(r)
        db_session.commit()

        _make_room(db_session, "room-A", topic="travel",
                   tags=["travel", "culture"], english_level=EnglishLevel.B2)
        _make_room(db_session, "room-B", topic="travel",
                   tags=["travel", "culture"], english_level=EnglishLevel.B2)

        result = run_matchmaking_tick()
        assert result == 2  # both matched

        r1 = db_session.exec(select(Room).where(Room.livekit_room_name == "room-A")).one()
        r2 = db_session.exec(select(Room).where(Room.livekit_room_name == "room-B")).one()
        assert r1.status == RoomStatus.ACTIVE
        assert r2.status == RoomStatus.ACTIVE

    def test_no_overlap_no_match(self, db_session):
        """Two rooms with nothing in common → not matched."""
        rooms = db_session.exec(select(Room)).all()
        for r in rooms:
            db_session.delete(r)
        db_session.commit()

        _make_room(db_session, "room-X", topic="sports",
                   tags=["football"], english_level=EnglishLevel.A1)
        _make_room(db_session, "room-Y", topic="cooking",
                   tags=["baking"], english_level=EnglishLevel.C2)

        result = run_matchmaking_tick()
        assert result == 0  # no match — combined score < 0.3

        r1 = db_session.exec(select(Room).where(Room.livekit_room_name == "room-X")).one()
        r2 = db_session.exec(select(Room).where(Room.livekit_room_name == "room-Y")).one()
        assert r1.status == RoomStatus.MATCHING
        assert r2.status == RoomStatus.MATCHING

    def test_topic_match_with_different_tags(self, db_session):
        """Same topic + English level proximity → matched even if tags differ."""
        rooms = db_session.exec(select(Room)).all()
        for r in rooms:
            db_session.delete(r)
        db_session.commit()

        _make_room(db_session, "room-P", topic="music",
                   tags=["pop"], english_level=EnglishLevel.B1)
        _make_room(db_session, "room-Q", topic="music",
                   tags=["rock"], english_level=EnglishLevel.B2)

        result = run_matchmaking_tick()
        # topic(0.30) + english proximity B1-B2(0.8→×0.25=0.20) + tier(0.15) = 0.65 > 0.3
        assert result == 2

    def test_three_rooms_best_pair_matched(self, db_session):
        """Three MATCHING rooms → the best pair is matched, third stays."""
        rooms = db_session.exec(select(Room)).all()
        for r in rooms:
            db_session.delete(r)
        db_session.commit()

        _make_room(db_session, "room-1", topic="travel",
                   tags=["travel", "culture"], english_level=EnglishLevel.B2)
        _make_room(db_session, "room-2", topic="travel",
                   tags=["travel", "culture"], english_level=EnglishLevel.B2)
        _make_room(db_session, "room-3", topic="cooking",
                   tags=["baking"], english_level=EnglishLevel.A1)

        result = run_matchmaking_tick()
        # rooms 1 & 2 should match (perfect), room 3 stays MATCHING
        assert result == 2

        r3 = db_session.exec(select(Room).where(Room.livekit_room_name == "room-3")).one()
        assert r3.status == RoomStatus.MATCHING

    def test_rooms_already_matched_not_re_matched(self, db_session):
        """Don't re-match rooms that already transitioned in the same tick."""
        rooms = db_session.exec(select(Room)).all()
        for r in rooms:
            db_session.delete(r)
        db_session.commit()

        _make_room(db_session, "room-AA", topic="sports",
                   tags=["football"], english_level=EnglishLevel.B1)
        _make_room(db_session, "room-BB", topic="sports",
                   tags=["basketball"], english_level=EnglishLevel.B1)
        # The guard in the matching loop should prevent double-counting

        result = run_matchmaking_tick()
        assert result == 2  # pair matched

    def test_matchmaking_only_affects_matching_rooms(self, db_session):
        """Rooms in ACTIVE or IDLE status are not matched."""
        rooms = db_session.exec(select(Room)).all()
        for r in rooms:
            db_session.delete(r)
        db_session.commit()

        _make_room(db_session, "active-1", topic="sports",
                   tags=["football"], english_level=EnglishLevel.B1,
                   status=RoomStatus.ACTIVE)
        _make_room(db_session, "active-2", topic="sports",
                   tags=["football"], english_level=EnglishLevel.B1,
                   status=RoomStatus.ACTIVE)

        result = run_matchmaking_tick()
        assert result == 0  # no MATCHING rooms

    def test_mixed_signals_prefer_english_match(self, db_session):
        """When topic differs but English is close AND tags overlap → still matches."""
        rooms = db_session.exec(select(Room)).all()
        for r in rooms:
            db_session.delete(r)
        db_session.commit()

        _make_room(db_session, "room-E1", topic="sports",
                   tags=["speaking", "pronunciation"], english_level=EnglishLevel.B2)
        _make_room(db_session, "room-E2", topic="fashion",
                   tags=["speaking", "pronunciation"], english_level=EnglishLevel.B2)

        result = run_matchmaking_tick()
        # tag Jaccard(2/2) = 0.30 + english proximity(1.0) = 0.25 + tier = 0.15 = 0.70 > 0.3
        assert result == 2
