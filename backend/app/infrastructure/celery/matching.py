from __future__ import annotations

import itertools
from datetime import datetime, timezone

from celery import shared_task
from sqlmodel import Session, select

from app.database import engine
from app.log import get_logger
from app.model.common import EnglishLevel, SubscriptionTier
from app.model.room import Room, RoomStatus

logger = get_logger(__name__)

_ENGLISH_LEVEL_MAP: dict[EnglishLevel, int] = {
    EnglishLevel.A1: 0,
    EnglishLevel.A2: 1,
    EnglishLevel.B1: 2,
    EnglishLevel.B2: 3,
    EnglishLevel.C1: 4,
    EnglishLevel.C2: 5,
}

_TIER_MAP: dict[SubscriptionTier, int] = {
    SubscriptionTier.FREE: 0,
    SubscriptionTier.PRO: 1,
    SubscriptionTier.PRO_PLUS: 2,
}

_ENGLISH_LEVELS = list(EnglishLevel)

_WEIGHT_TOPIC = 0.30
_WEIGHT_TAG = 0.30
_WEIGHT_ENGLISH = 0.25
_WEIGHT_TIER = 0.15

_MATCH_THRESHOLD_INITIAL = 0.3
_MATCH_THRESHOLD_CROSS_TAG = 0.15
_MATCH_THRESHOLD_FALLBACK = 0.05

_FALLBACK_TIMINGS = {
    "cross_tag": 30,
    "level_expand": 45,
    "ai_room": 60,
}


def _seconds_since(dt: datetime | None) -> int:
    if dt is None:
        return 9999
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int((now - dt).total_seconds())


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _extract_tags(room: Room) -> set[str]:
    if not room.tags:
        return set()
    return {t.lower().strip() for t in room.tags if t}


def _english_proximity(level1: EnglishLevel | None, level2: EnglishLevel | None) -> float:
    if level1 is None or level2 is None:
        return 0.5
    diff = abs(_ENGLISH_LEVEL_MAP[level1] - _ENGLISH_LEVEL_MAP[level2])
    return 1.0 - diff / 5.0


def _tier_score(tier1: SubscriptionTier, tier2: SubscriptionTier) -> float:
    diff = abs(_TIER_MAP[tier1] - _TIER_MAP[tier2])
    return 1.0 - diff / 2.0


def _level_is_adjacent(l1: EnglishLevel | None, l2: EnglishLevel | None) -> bool:
    if l1 is None or l2 is None:
        return True
    return abs(_ENGLISH_LEVEL_MAP[l1] - _ENGLISH_LEVEL_MAP[l2]) <= 1


def _find_fallback_level(level: EnglishLevel | None) -> list[EnglishLevel | None]:
    if level is None:
        return [None]
    idx = _ENGLISH_LEVEL_MAP[level]
    start = max(0, idx - 1)
    end = min(len(_ENGLISH_LEVELS) - 1, idx + 1)
    return list(_ENGLISH_LEVELS[start : end + 1])


def _compute_score(
    topic_sim: float,
    tag_sim: float,
    english_sim: float,
    tier_sim: float,
) -> float:
    return (
        _WEIGHT_TOPIC * topic_sim
        + _WEIGHT_TAG * tag_sim
        + _WEIGHT_ENGLISH * english_sim
        + _WEIGHT_TIER * tier_sim
    )


def _initial_match(rooms: list[Room], tier_cache: dict) -> list[tuple[Room, Room, float]]:
    pairs = []
    for r1, r2 in itertools.combinations(rooms, 2):
        if r1.status != RoomStatus.MATCHING or r2.status != RoomStatus.MATCHING:
            continue

        topic_sim = 1.0 if (
            r1.topic and r2.topic and r1.topic.strip().lower() == r2.topic.strip().lower()
        ) else 0.0

        tag_sim = _jaccard(_extract_tags(r1), _extract_tags(r2))
        t1 = r1.creator_user_id
        t2 = r2.creator_user_id
        tier1 = tier_cache.get(t1, SubscriptionTier.FREE) if t1 else SubscriptionTier.FREE
        tier2 = tier_cache.get(t2, SubscriptionTier.FREE) if t2 else SubscriptionTier.FREE
        tier_sim = _tier_score(tier1, tier2)
        english_sim = _english_proximity(r1.english_level, r2.english_level)

        combined = _compute_score(topic_sim, tag_sim, english_sim, tier_sim)

        if combined > _MATCH_THRESHOLD_INITIAL:
            pairs.append((r1, r2, combined))

    return pairs


def _cross_tag_match(rooms: list[Room], tier_cache: dict) -> list[tuple[Room, Room, float]]:
    pairs = []
    for r1, r2 in itertools.combinations(rooms, 2):
        if r1.status != RoomStatus.MATCHING or r2.status != RoomStatus.MATCHING:
            continue

        t1 = r1.creator_user_id
        t2 = r2.creator_user_id
        tier1 = tier_cache.get(t1, SubscriptionTier.FREE) if t1 else SubscriptionTier.FREE
        tier2 = tier_cache.get(t2, SubscriptionTier.FREE) if t2 else SubscriptionTier.FREE
        tier_sim = _tier_score(tier1, tier2)
        english_sim = _english_proximity(r1.english_level, r2.english_level)

        combined = _compute_score(0.0, 0.0, english_sim, tier_sim)

        if combined > _MATCH_THRESHOLD_CROSS_TAG:
            pairs.append((r1, r2, combined))

    return pairs


def _level_expand_match(rooms: list[Room], tier_cache: dict) -> list[tuple[Room, Room, float]]:
    pairs = []
    for r1, r2 in itertools.combinations(rooms, 2):
        if r1.status != RoomStatus.MATCHING or r2.status != RoomStatus.MATCHING:
            continue

        if _level_is_adjacent(r1.english_level, r2.english_level):
            t1 = r1.creator_user_id
            t2 = r2.creator_user_id
            tier1 = tier_cache.get(t1, SubscriptionTier.FREE) if t1 else SubscriptionTier.FREE
            tier2 = tier_cache.get(t2, SubscriptionTier.FREE) if t2 else SubscriptionTier.FREE
            tier_sim = _tier_score(tier1, tier2)
            english_sim = _english_proximity(r1.english_level, r2.english_level)

            combined = _compute_score(0.0, 0.0, english_sim, tier_sim)

            if combined > _MATCH_THRESHOLD_FALLBACK:
                pairs.append((r1, r2, combined))

    return pairs


def _mark_matched(session: Session, r1: Room, r2: Room) -> int:
    r1.status = RoomStatus.ACTIVE
    r2.status = RoomStatus.ACTIVE
    session.add_all([r1, r2])
    return 2


@shared_task(name="eroom.run_matchmaking_tick", bind=True, max_retries=2, default_retry_delay=5)
def run_matchmaking_tick(self) -> int:
    matched_count = 0
    try:
        with Session(engine) as session:
            waiting_rooms = session.exec(
                select(Room).where(Room.status == RoomStatus.MATCHING)
            ).all()

            if len(waiting_rooms) < 2:
                return 0

            user_ids = {r.creator_user_id for r in waiting_rooms if r.creator_user_id}
            tier_cache: dict = {}

            if user_ids:
                from app.model.subscription import Subscription

                subs = session.exec(
                    select(Subscription).where(Subscription.user_id.in_(user_ids))
                ).all()
                tier_cache = {s.user_id: s.tier for s in subs}

            now_ts = _seconds_since(datetime.now(timezone.utc))

            initial_waiting = [r for r in waiting_rooms if _seconds_since(r.started_at) < _FALLBACK_TIMINGS["cross_tag"]]
            cross_tag_waiting = [
                r for r in waiting_rooms
                if _FALLBACK_TIMINGS["cross_tag"] <= _seconds_since(r.started_at) < _FALLBACK_TIMINGS["level_expand"]
            ]
            level_expand_waiting = [
                r for r in waiting_rooms
                if _FALLBACK_TIMINGS["level_expand"] <= _seconds_since(r.started_at) < _FALLBACK_TIMINGS["ai_room"]
            ]
            ai_room_waiting = [
                r for r in waiting_rooms
                if _seconds_since(r.started_at) >= _FALLBACK_TIMINGS["ai_room"]
            ]

            initial_pairs = _initial_match(initial_waiting, tier_cache)
            for r1, r2, score in initial_pairs:
                matched_count += _mark_matched(session, r1, r2)

            cross_tag_pairs = _cross_tag_match(cross_tag_waiting, tier_cache)
            for r1, r2, score in cross_tag_pairs:
                matched_count += _mark_matched(session, r1, r2)

            level_expand_pairs = _level_expand_match(level_expand_waiting, tier_cache)
            for r1, r2, score in level_expand_pairs:
                matched_count += _mark_matched(session, r1, r2)

            for room in ai_room_waiting:
                if room.status == RoomStatus.MATCHING:
                    room.status = RoomStatus.ACTIVE
                    room.topic = f"AI-hosted: {room.topic or 'English Practice'}"
                    session.add(room)
                    matched_count += 1

            session.commit()

        logger.info("Ghép cặp hoàn tất", extra={
            "matched": matched_count,
            "initial": len(initial_pairs) * 2,
            "cross_tag": len(cross_tag_pairs) * 2,
            "level_expand": len(level_expand_pairs) * 2,
            "ai_rooms": len(ai_room_waiting),
        })
    except Exception as e:
        logger.error("Ghép cặp thất bại", exc_info=True)
        raise self.retry(exc=e)

    return matched_count
