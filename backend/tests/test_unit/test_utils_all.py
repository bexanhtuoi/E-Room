from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.utils.datetime_utils import (
    format_duration,
    format_relative,
    is_expired,
    now_saigon,
    now_utc,
    timestamp_ms,
    ttl_seconds,
    utc_to_saigon,
    week_boundaries_monday,
)
from app.utils.text import (
    highlight_difference,
    levenshtein_ratio,
    normalize_whitespace,
    sanitize_html,
    sentence_count,
    slugify,
    truncate,
    word_count,
)
from app.utils.validation import (
    clamp,
    is_valid_email,
    is_valid_uuid,
    sanitize_string,
    validate_display_name,
    validate_password_strength,
)


class TestDatetimeUtils:
    def test_now_utc_returns_aware_datetime(self):
        dt = now_utc()
        assert dt.tzinfo is not None
        assert dt.tzinfo.utcoffset(dt) == timedelta(0)

    def test_now_saigon_returns_saigon_timezone(self):
        dt = now_saigon()
        assert dt.tzinfo is not None
        assert dt.tzinfo.utcoffset(dt).total_seconds() == 7 * 3600

    def test_utc_to_saigon_naive_input(self):
        naive = datetime(2026, 5, 12, 12, 0, 0)
        result = utc_to_saigon(naive)
        assert result.hour == 19

    def test_utc_to_saigon_aware_input(self):
        aware = datetime(2026, 5, 12, 12, 0, 0, tzinfo=UTC)
        result = utc_to_saigon(aware)
        assert result.hour == 19

    def test_timestamp_ms_returns_milliseconds(self):
        ts = timestamp_ms()
        assert 1_700_000_000_000 < ts < 2_000_000_000_000

    def test_format_duration_seconds_only(self):
        assert format_duration(45) == "45s"

    def test_format_duration_minutes_seconds(self):
        assert format_duration(125) == "2m 5s"

    def test_format_duration_hours_minutes_seconds(self):
        assert format_duration(3725) == "1h 2m 5s"

    def test_format_duration_zero(self):
        assert format_duration(0) == "0s"

    def test_format_relative_years(self):
        result = format_relative(31536000 * 2)
        assert "năm" in result

    def test_format_relative_just_now(self):
        assert format_relative(10) == "vừa xong"

    def test_format_relative_minutes(self):
        result = format_relative(120)
        assert "phút" in result

    def test_week_boundaries_monday_returns_monday_start(self):
        ref = datetime(2026, 5, 13, 14, 30, tzinfo=UTC)
        monday, sunday = week_boundaries_monday(ref)
        assert monday.day == 11
        assert monday.hour == 0
        assert sunday.hour == 23

    def test_is_expired_future_not_expired(self):
        future = now_utc() + timedelta(hours=1)
        assert not is_expired(future)

    def test_is_expired_past_expired(self):
        past = now_utc() - timedelta(seconds=1)
        assert is_expired(past)

    def test_is_expired_with_grace(self):
        past = now_utc() - timedelta(seconds=30)
        assert not is_expired(past, grace_seconds=60)

    def test_ttl_seconds_returns_positive(self):
        future = now_utc() + timedelta(hours=2)
        assert ttl_seconds(future) > 0

    def test_ttl_seconds_expired_returns_zero(self):
        past = now_utc() - timedelta(hours=1)
        assert ttl_seconds(past) == 0


class TestTextUtils:
    def test_truncate_short(self):
        assert truncate("hello", 10) == "hello"

    def test_truncate_long(self):
        result = truncate("hello world this is long", 12)
        assert result.endswith("…")
        assert len(result) <= 13

    def test_truncate_custom_ellipsis(self):
        result = truncate("hello world test", 10, ellipsis="...")
        assert result.endswith("...")

    def test_word_count_empty(self):
        assert word_count("") == 0

    def test_word_count_simple(self):
        assert word_count("hello world") == 2

    def test_word_count_special_chars(self):
        assert word_count("hello-world isn't great") == 5

    def test_sentence_count_empty(self):
        assert sentence_count("") == 0

    def test_sentence_count_single(self):
        assert sentence_count("Hello world.") == 1

    def test_sentence_count_multiple(self):
        assert sentence_count("Hi! How are you? I'm fine.") == 3

    def test_levenshtein_ratio_identical(self):
        assert levenshtein_ratio("hello", "hello") == 1.0

    def test_levenshtein_ratio_completely_different(self):
        assert levenshtein_ratio("abc", "xyz") < 0.5

    def test_levenshtein_ratio_both_empty(self):
        assert levenshtein_ratio("", "") == 1.0

    def test_levenshtein_ratio_one_empty(self):
        assert levenshtein_ratio("hello", "") == 0.0

    def test_normalize_whitespace(self):
        assert normalize_whitespace("  hello   world  ") == "hello world"

    def test_sanitize_html_ampersand(self):
        assert "&amp;" in sanitize_html("a & b")

    def test_sanitize_html_tags(self):
        assert sanitize_html("<script>") == "&lt;script&gt;"

    def test_slugify_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_slugify_special_chars(self):
        assert slugify("Hello, World!!") == "hello-world"

    def test_slugify_multiple_hyphens(self):
        assert slugify("a---b") == "a-b"

    def test_highlight_difference_same(self):
        result = highlight_difference("hello", "hello")
        assert result["diff"] == "same"

    def test_highlight_difference_minor(self):
        result = highlight_difference("hello world", "hello World!")
        assert result["diff"] in ("minor", "major")

    def test_highlight_difference_major(self):
        result = highlight_difference("good morning", "goodbye")
        assert result["diff"] == "major"


class TestValidationUtils:
    def test_is_valid_email_ok(self):
        assert is_valid_email("user@example.com")

    def test_is_valid_email_no_at(self):
        assert not is_valid_email("userexample.com")

    def test_is_valid_email_too_long(self):
        long = "a" * 250 + "@b.com"
        assert not is_valid_email(long)

    def test_is_valid_uuid_ok(self):
        assert is_valid_uuid("550e8400-e29b-41d4-a716-446655440000")

    def test_is_valid_uuid_invalid(self):
        assert not is_valid_uuid("not-a-uuid")

    def test_is_valid_uuid_empty(self):
        assert not is_valid_uuid("")

    def test_sanitize_string_trims(self):
        result = sanitize_string("  hello  ")
        assert result == "hello"

    def test_sanitize_string_control_chars(self):
        result = sanitize_string("hel\x00lo")
        assert result == "hello"

    def test_sanitize_string_truncates(self):
        result = sanitize_string("a" * 2000, max_length=100)
        assert len(result) == 100

    def test_validate_password_too_short(self):
        valid, msg = validate_password_strength("Ab1")
        assert not valid
        assert "8 ký tự" in msg

    def test_validate_password_no_uppercase(self):
        valid, msg = validate_password_strength("abcdefgh1")
        assert not valid
        assert "chữ hoa" in msg

    def test_validate_password_no_number(self):
        valid, msg = validate_password_strength("Abcdefgh")
        assert not valid
        assert "số" in msg

    def test_validate_password_ok(self):
        valid, msg = validate_password_strength("StrongPass1")
        assert valid
        assert msg is None

    def test_validate_display_name_empty(self):
        valid, msg = validate_display_name("")
        assert not valid

    def test_validate_display_name_too_short(self):
        valid, msg = validate_display_name("A")
        assert not valid

    def test_validate_display_name_too_long(self):
        valid, msg = validate_display_name("A" * 60)
        assert not valid

    def test_validate_display_name_invalid_chars(self):
        valid, msg = validate_display_name("<script>")
        assert not valid

    def test_validate_display_name_ok(self):
        valid, msg = validate_display_name("Valid Name")
        assert valid

    def test_clamp_within_range(self):
        assert clamp(5.0, 0.0, 10.0) == 5.0

    def test_clamp_below_min(self):
        assert clamp(-5.0, 0.0, 10.0) == 0.0

    def test_clamp_above_max(self):
        assert clamp(15.0, 0.0, 10.0) == 10.0

    def test_clamp_defaults(self):
        assert clamp(7.5) == 7.5
