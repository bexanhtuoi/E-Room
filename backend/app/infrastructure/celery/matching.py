from __future__ import annotations

import itertools

from celery import shared_task
from sqlmodel import Session, select

from app.database import engine
from app.log import get_logger
from app.model.common import EnglishLevel, SubscriptionTier
from app.model.room import Room, RoomStatus
from app.model.subscription import Subscription

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

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

_MAX_ENGLISH_DIFF = 5   # A1 (0) → C2 (5)
_MAX_TIER_DIFF = 2       # FREE (0) → PRO_PLUS (2)

# Scoring weights — must sum to 1.0
_WEIGHT_TOPIC    = 0.30
_WEIGHT_TAG      = 0.30
_WEIGHT_ENGLISH  = 0.25
_WEIGHT_TIER     = 0.15

_MATCH_THRESHOLD = 0.3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity coefficient."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _extract_tags(room: Room) -> set[str]:
    """Extract normalized tag strings from a room (tags stored as list[str])."""
    if not room.tags:
        return set()
    return {t.lower().strip() for t in room.tags if t}


def _english_proximity(level1: EnglishLevel | None, level2: EnglishLevel | None) -> float:
    """Proximity score for English levels (0–1).
    
    Returns 0.5 (neutral) when either level is unset.
    Otherwise: 1.0 − |index_diff| / max_diff.
    """
    if level1 is None or level2 is None:
        return 0.5
    diff = abs(_ENGLISH_LEVEL_MAP[level1] - _ENGLISH_LEVEL_MAP[level2])
    return 1.0 - diff / _MAX_ENGLISH_DIFF


def _tier_score(tier1: SubscriptionTier, tier2: SubscriptionTier) -> float:
    """Subscription-tier affinity score (0–1)."""
    diff = abs(_TIER_MAP[tier1] - _TIER_MAP[tier2])
    return 1.0 - diff / _MAX_TIER_DIFF


# ---------------------------------------------------------------------------
# Celery task
# ---------------------------------------------------------------------------

@shared_task(name="eroom.run_matchmaking_tick", bind=True, max_retries=2, default_retry_delay=5)
def run_matchmaking_tick(self) -> int:
    """Run one matchmaking tick — pair MATCHING rooms with multi-factor scoring.

    Scoring factors (weights):
      • Topic  (0.30) – exact case-insensitive topic match
      • Tags   (0.30) – Jaccard similarity over tag sets
      • English(0.25) – proximity of room English levels (A1→C2)
      • Tier   (0.15) – subscription tier affinity (FREE/PRO/PRO_PLUS)
    """
    matched_count = 0
    try:
        with Session(engine) as session:
            waiting_rooms = session.exec(
                select(Room).where(Room.status == RoomStatus.MATCHING)
            ).all()
            if len(waiting_rooms) < 2:
                return 0

            # Pre-fetch subscription tiers to avoid N+1
            user_ids = {r.creator_user_id for r in waiting_rooms if r.creator_user_id}
            tier_cache: dict = {}
            if user_ids:
                subs = session.exec(
                    select(Subscription).where(Subscription.user_id.in_(user_ids))
                ).all()
                tier_cache = {s.user_id: s.tier for s in subs}

            def _get_tier(room: Room) -> SubscriptionTier:
                if room.creator_user_id and room.creator_user_id in tier_cache:
                    return tier_cache[room.creator_user_id]
                return SubscriptionTier.FREE

            for r1, r2 in itertools.combinations(waiting_rooms, 2):
                if r1.status != RoomStatus.MATCHING or r2.status != RoomStatus.MATCHING:
                    continue

                topic_sim = 1.0 if (
                    r1.topic
                    and r2.topic
                    and r1.topic.strip().lower() == r2.topic.strip().lower()
                ) else 0.0

                tag_sim = _jaccard(_extract_tags(r1), _extract_tags(r2))

                english_sim = _english_proximity(r1.english_level, r2.english_level)

                tier_sim = _tier_score(_get_tier(r1), _get_tier(r2))

                combined = (
                    _WEIGHT_TOPIC * topic_sim
                    + _WEIGHT_TAG * tag_sim
                    + _WEIGHT_ENGLISH * english_sim
                    + _WEIGHT_TIER * tier_sim
                )

                if combined > _MATCH_THRESHOLD:
                    r1.status = RoomStatus.ACTIVE
                    r2.status = RoomStatus.ACTIVE
                    session.add_all([r1, r2])
                    matched_count += 2
                    logger.debug("matchmaking_pair", extra={
                        "room1": r1.livekit_room_name,
                        "room2": r2.livekit_room_name,
                        "score": round(combined, 3),
                        "topic": round(topic_sim, 2),
                        "tags": round(tag_sim, 2),
                        "english": round(english_sim, 2),
                        "tier": round(tier_sim, 2),
                    })

            session.commit()
        logger.info("matchmaking_tick_done", extra={"matched": matched_count})
    except Exception as e:
        logger.error("matchmaking_tick_failed", exc_info=True)
        raise self.retry(exc=e)
    return matched_count