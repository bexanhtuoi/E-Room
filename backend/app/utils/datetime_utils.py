from datetime import UTC, datetime


def now_utc() -> datetime:
    return datetime.now(UTC)


def as_naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.replace(tzinfo=None)

    return value
