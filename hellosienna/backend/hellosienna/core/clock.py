"""Clock abstraction (M0, acceptance #13).

The single source of "now" for the whole system. All timestamps are timezone-aware
UTC. Direct datetime.now()/utcnow() is banned in core/ (and, later, jobs/ and
scheduler/); a test greps for violations.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime:
        """Return the current time as a timezone-aware UTC datetime."""
        ...


class SystemClock:
    """Production clock: real wall-clock time in UTC."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class TestClock:
    """Deterministic clock for tests and the demo's time-advance.

    Defaults to the UNIX epoch (UTC) so tests are reproducible.
    """

    __test__ = False  # not a pytest test class despite the "Test" prefix

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(1970, 1, 1, tzinfo=timezone.utc)
        if self._now.tzinfo is None:
            raise ValueError("TestClock requires a timezone-aware datetime")

    def now(self) -> datetime:
        return self._now

    def set(self, when: datetime) -> None:
        if when.tzinfo is None:
            raise ValueError("Clock time must be timezone-aware (UTC)")
        self._now = when.astimezone(timezone.utc)

    def advance(self, delta: timedelta) -> None:
        self._now = self._now + delta


def isoformat_utc(dt: datetime) -> str:
    """Render a UTC datetime as ISO-8601 with a trailing 'Z' (storage convention)."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
