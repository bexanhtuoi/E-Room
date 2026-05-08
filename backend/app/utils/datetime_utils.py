from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

_TZ_SAIGON = ZoneInfo("Asia/Ho_Chi_Minh")


def now_utc() -> datetime:
    return datetime.now(UTC)


def now_saigon() -> datetime:
    return datetime.now(_TZ_SAIGON)


def utc_to_saigon(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(_TZ_SAIGON)


def saigon_to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_TZ_SAIGON)
    return dt.astimezone(UTC)


def timestamp_ms() -> int:
    return int(now_utc().timestamp() * 1000)


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m {secs}s"


def format_relative(seconds: int) -> str:
    intervals = [
        ("năm", 31536000),
        ("tháng", 2592000),
        ("tuần", 604800),
        ("ngày", 86400),
        ("giờ", 3600),
        ("phút", 60),
    ]
    for name, count in intervals:
        value = seconds // count
        if value >= 1:
            return f"{value} {name} trước"
    return "vừa xong"


def week_boundaries_monday(reference: datetime | None = None) -> tuple[datetime, datetime]:
    ref = reference or now_utc()
    monday = ref - timedelta(days=ref.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday


def is_expired(expires_at: datetime, grace_seconds: int = 0) -> bool:
    return now_utc() > expires_at + timedelta(seconds=grace_seconds)


def ttl_seconds(expires_at: datetime) -> int:
    return max(0, int((expires_at - now_utc()).total_seconds()))
