"""Acceptance #13 (guard): no direct datetime.now()/utcnow() in core/ (and, later,
jobs/ and scheduler/). All 'now' must go through the Clock. clock.py itself is the
one allowed home for the wall-clock read."""
from __future__ import annotations

import re
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
SCANNED_DIRS = ["hellosienna/core"]  # jobs/ and scheduler/ added when they exist (M2/M3)
PATTERN = re.compile(r"datetime\.(now|utcnow)\s*\(")
ALLOWED = {"clock.py"}


def test_no_direct_wallclock_reads_in_core():
    offenders = []
    for rel in SCANNED_DIRS:
        for py in (BACKEND / rel).rglob("*.py"):
            if py.name in ALLOWED:
                continue
            if PATTERN.search(py.read_text(encoding="utf-8")):
                offenders.append(str(py.relative_to(BACKEND)))
    assert not offenders, f"direct datetime.now/utcnow found in core: {offenders}"
