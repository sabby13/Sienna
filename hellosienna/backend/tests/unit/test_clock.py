"""Acceptance #13: Clock works with SystemClock and TestClock."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from hellosienna.core.clock import SystemClock, TestClock, isoformat_utc


def test_system_clock_is_utc_aware_and_current():
    now = SystemClock().now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)
    delta = abs((datetime.now(timezone.utc) - now).total_seconds())
    assert delta < 5


def test_test_clock_set_and_advance_are_deterministic():
    c = TestClock(datetime(2026, 9, 7, 9, 0, tzinfo=timezone.utc))
    assert isoformat_utc(c.now()) == "2026-09-07T09:00:00Z"
    c.advance(timedelta(days=1, hours=2))
    assert isoformat_utc(c.now()) == "2026-09-08T11:00:00Z"
    c.set(datetime(2030, 1, 1, tzinfo=timezone.utc))
    assert isoformat_utc(c.now()) == "2030-01-01T00:00:00Z"


def test_test_clock_rejects_naive_datetime():
    import pytest
    with pytest.raises(ValueError):
        TestClock(datetime(2026, 1, 1))  # naive
