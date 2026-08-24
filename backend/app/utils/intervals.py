"""Half-open interval [start, end) utilities.

All appointment/hold overlap logic in this codebase must go through this
module so the overlap semantics stay consistent everywhere.
"""
from datetime import datetime
from typing import NamedTuple


class Interval(NamedTuple):
    start: datetime
    end: datetime


def overlaps(a: Interval, b: Interval) -> bool:
    """Two half-open intervals [start, end) overlap iff:
    a.start < b.end AND a.end > b.start
    """
    return a.start < b.end and a.end > b.start


def overlaps_any(candidate: Interval, taken: list[Interval]) -> bool:
    """O(n) scan against a pre-fetched, small list of busy intervals for one day.
    For a single doctor/day this list is bounded (appointments + holds for
    that day), so this stays fast without needing a database round trip per
    candidate slot.
    """
    return any(overlaps(candidate, t) for t in taken)
