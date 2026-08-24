from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(dt: datetime) -> datetime:
    """Normalize a datetime to UTC, treating naive datetimes as UTC.

    We never compare naive vs aware timestamps in this codebase — every
    datetime that crosses a service boundary passes through here first.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
