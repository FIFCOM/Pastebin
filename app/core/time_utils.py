"""
Time utilities.

SQLite stores datetimes without timezone information (naive datetimes). Some
code uses timezone-aware `datetime.now(UTC)`, which raises when compared to
naive values. Helpers here normalize values for safe comparisons while treating
naive datetimes as UTC.
"""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


def coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def is_expired(expires_at: datetime | None, *, now: datetime | None = None) -> bool:
    if expires_at is None:
        return False
    now_dt = utc_now() if now is None else now
    return coerce_utc(now_dt) > coerce_utc(expires_at)

