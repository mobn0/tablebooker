"""Pure scheduling logic (no DB access, easy to unit test)."""
from datetime import time
from typing import Iterable

from .models import DiningTable


def to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def overlaps(start_a: time, duration_a: int, start_b: time, duration_b: int) -> bool:
    """Two slots overlap if they share any time. Touching slots (end == start) do not."""
    a_start, b_start = to_minutes(start_a), to_minutes(start_b)
    return a_start < b_start + duration_b and b_start < a_start + duration_a


def within_opening_hours(start: time, duration: int, opening: time, closing: time) -> bool:
    """The whole reservation (start until end) must lie inside opening hours."""
    return to_minutes(opening) <= to_minutes(start) and to_minutes(start) + duration <= to_minutes(closing)


class TableAllocator:
    """Finds the best-fitting free table for a party."""

    def find_best_table(
        self,
        tables: Iterable[DiningTable],
        party_size: int,
        busy_table_ids: set[int],
    ) -> DiningTable | None:
        candidates = [t for t in tables if t.seats >= party_size and t.id not in busy_table_ids]
        if not candidates:
            return None
        # fewest seats first (least waste), then lowest table number
        return min(candidates, key=lambda t: (t.seats, t.number))
