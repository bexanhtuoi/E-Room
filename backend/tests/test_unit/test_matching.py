from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from app.model.common import EnglishLevel, SubscriptionTier


class TestJaccard:
    def test_identical_sets(self):
        from app.infrastructure.celery.matching import _jaccard
        assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint_sets(self):
        from app.infrastructure.celery.matching import _jaccard
        assert _jaccard({"a"}, {"b"}) == 0.0

    def test_partial_overlap(self):
        from app.infrastructure.celery.matching import _jaccard
        assert _jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)

    def test_both_empty(self):
        from app.infrastructure.celery.matching import _jaccard
        assert _jaccard(set(), set()) == 1.0

    def test_one_empty(self):
        from app.infrastructure.celery.matching import _jaccard
        assert _jaccard({"a"}, set()) == 0.0


class TestEnglishProximity:
    def test_same_level(self):
        from app.infrastructure.celery.matching import _english_proximity
        assert _english_proximity(EnglishLevel.B1, EnglishLevel.B1) == 1.0

    def test_adjacent_levels(self):
        from app.infrastructure.celery.matching import _english_proximity
        # B1(2) – B2(3): diff=1 → 1 − 1/5 = 0.8
        assert _english_proximity(EnglishLevel.B1, EnglishLevel.B2) == pytest.approx(0.8)

    def test_max_distance(self):
        from app.infrastructure.celery.matching import _english_proximity
        # A1(0) – C2(5): diff=5 → 1 − 5/5 = 0.0
        assert _english_proximity(EnglishLevel.A1, EnglishLevel.C2) == pytest.approx(0.0)

    def test_none_returns_neutral(self):
        from app.infrastructure.celery.matching import _english_proximity
        assert _english_proximity(None, EnglishLevel.B1) == 0.5
        assert _english_proximity(EnglishLevel.B1, None) == 0.5
        assert _english_proximity(None, None) == 0.5

    def test_a1_to_c2_range(self):
        from app.infrastructure.celery.matching import _english_proximity
        # A1(0) – A2(1): diff=1 → 0.8
        assert _english_proximity(EnglishLevel.A1, EnglishLevel.A2) == pytest.approx(0.8)
        # A2(1) – C1(4): diff=3 → 0.4
        assert _english_proximity(EnglishLevel.A2, EnglishLevel.C1) == pytest.approx(0.4)
        # B2(3) – C2(5): diff=2 → 0.6
        assert _english_proximity(EnglishLevel.B2, EnglishLevel.C2) == pytest.approx(0.6)


class TestTierScore:
    def test_same_tier(self):
        from app.infrastructure.celery.matching import _tier_score
        assert _tier_score(SubscriptionTier.PRO, SubscriptionTier.PRO) == 1.0

    def test_adjacent_tiers(self):
        from app.infrastructure.celery.matching import _tier_score
        # FREE(0) – PRO(1): diff=1 → 1 − 1/2 = 0.5
        assert _tier_score(SubscriptionTier.FREE, SubscriptionTier.PRO) == pytest.approx(0.5)
        # PRO(1) – PRO_PLUS(2): diff=1 → 0.5
        assert _tier_score(SubscriptionTier.PRO, SubscriptionTier.PRO_PLUS) == pytest.approx(0.5)

    def test_max_tier_gap(self):
        from app.infrastructure.celery.matching import _tier_score
        # FREE(0) – PRO_PLUS(2): diff=2 → 1 − 2/2 = 0.0
        assert _tier_score(SubscriptionTier.FREE, SubscriptionTier.PRO_PLUS) == pytest.approx(0.0)


class TestExtractTags:
    def test_empty_tags(self):
        from app.infrastructure.celery.matching import _extract_tags
        from unittest.mock import MagicMock
        room = MagicMock()
        room.tags = []
        assert _extract_tags(room) == set()

    def test_normalization(self):
        from app.infrastructure.celery.matching import _extract_tags
        from unittest.mock import MagicMock
        room = MagicMock()
        room.tags = ["  JavaScript  ", "REACT", ""]
        result = _extract_tags(room)
        assert result == {"javascript", "react"}

    def test_none_tags(self):
        from app.infrastructure.celery.matching import _extract_tags
        from unittest.mock import MagicMock
        room = MagicMock()
        room.tags = None
        assert _extract_tags(room) == set()


class TestCombinedScoring:
    """End-to-end: verify scoring formula produces expected ranges."""

    def test_perfect_match_score(self):
        """Two rooms with identical topic, tags, english level, and tier → very high score."""
        from app.infrastructure.celery.matching import (
            _jaccard, _extract_tags, _english_proximity, _tier_score,
        )
        from unittest.mock import MagicMock

        r1 = MagicMock()
        r1.topic = "travel"
        r1.tags = ["travel", "culture"]
        r1.english_level = EnglishLevel.B2

        r2 = MagicMock()
        r2.topic = "travel"
        r2.tags = ["travel", "culture"]
        r2.english_level = EnglishLevel.B2

        topic_sim = 1.0
        tag_sim = _jaccard(_extract_tags(r1), _extract_tags(r2))
        english_sim = _english_proximity(r1.english_level, r2.english_level)
        tier_sim = _tier_score(SubscriptionTier.FREE, SubscriptionTier.FREE)

        combined = 0.30 * topic_sim + 0.30 * tag_sim + 0.25 * english_sim + 0.15 * tier_sim
        # 0.30 + 0.30 + 0.25 + 0.15 = 1.0
        assert combined == pytest.approx(1.0)

    def test_no_overlap_score(self):
        """Two rooms with nothing in common → very low score."""
        from app.infrastructure.celery.matching import (
            _jaccard, _extract_tags, _english_proximity, _tier_score,
        )
        from unittest.mock import MagicMock

        r1 = MagicMock()
        r1.topic = "sports"
        r1.tags = ["football"]
        r1.english_level = EnglishLevel.A1

        r2 = MagicMock()
        r2.topic = "cooking"
        r2.tags = ["baking"]
        r2.english_level = EnglishLevel.C2

        topic_sim = 0.0
        tag_sim = _jaccard(_extract_tags(r1), _extract_tags(r2))
        english_sim = _english_proximity(r1.english_level, r2.english_level)
        tier_sim = _tier_score(SubscriptionTier.FREE, SubscriptionTier.FREE)

        combined = 0.30 * topic_sim + 0.30 * tag_sim + 0.25 * english_sim + 0.15 * tier_sim
        # 0 + 0 + 0 + 0.15 = 0.15 < 0.3 threshold
        assert combined < 0.3

    def test_threshold_boundary(self):
        """Weak but sufficient match: same topic + same tier, different tags & english."""
        from app.infrastructure.celery.matching import (
            _jaccard, _extract_tags, _english_proximity, _tier_score,
        )
        from unittest.mock import MagicMock

        r1 = MagicMock()
        r1.topic = "music"
        r1.tags = ["pop"]
        r1.english_level = EnglishLevel.A1

        r2 = MagicMock()
        r2.topic = "music"
        r2.tags = ["rock"]
        r2.english_level = EnglishLevel.C2

        topic_sim = 1.0
        tag_sim = _jaccard(_extract_tags(r1), _extract_tags(r2))
        english_sim = _english_proximity(r1.english_level, r2.english_level)
        tier_sim = _tier_score(SubscriptionTier.PRO, SubscriptionTier.PRO)

        combined = 0.30 * topic_sim + 0.30 * tag_sim + 0.25 * english_sim + 0.15 * tier_sim
        # 0.30 + 0 + 0 + 0.15 = 0.45 > 0.3
        assert combined > 0.3


class TestWeightsSumToOne:
    def test_weights_normalized(self):
        from app.infrastructure.celery import matching
        total = (
            matching._WEIGHT_TOPIC
            + matching._WEIGHT_TAG
            + matching._WEIGHT_ENGLISH
            + matching._WEIGHT_TIER
        )
        assert total == pytest.approx(1.0)
