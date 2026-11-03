from datetime import time

import pytest

from app.models import DiningTable
from app.scheduling import TableAllocator, overlaps, to_minutes, within_opening_hours


def make_table(id: int, seats: int, number: int = 1) -> DiningTable:
    return DiningTable(id=id, restaurant_id=1, number=number, seats=seats)


class TestToMinutes:
    @pytest.mark.parametrize(
        "t, expected",
        [
            pytest.param(time(0, 0), 0, id="midnight"),
            pytest.param(time(0, 1), 1, id="one-minute"),
            pytest.param(time(1, 0), 60, id="one-hour"),
            pytest.param(time(11, 30), 690, id="11:30"),
            pytest.param(time(18, 0), 1080, id="18:00"),
            pytest.param(time(23, 59), 1439, id="last-minute-of-day"),
        ],
    )
    def test_converts_to_minutes_since_midnight(self, t, expected):
        assert to_minutes(t) == expected

    def test_seconds_are_ignored(self):
        assert to_minutes(time(10, 15, 59)) == to_minutes(time(10, 15))

    def test_returns_int(self):
        assert isinstance(to_minutes(time(10, 15)), int)


class TestOverlaps:
    @pytest.mark.parametrize(
        "start_a, dur_a, start_b, dur_b",
        [
            pytest.param(time(18, 0), 90, time(18, 0), 90, id="identical-slots"),
            pytest.param(time(18, 0), 90, time(18, 30), 90, id="b-starts-inside-a"),
            pytest.param(time(18, 30), 90, time(18, 0), 90, id="a-starts-inside-b"),
            pytest.param(time(18, 0), 120, time(18, 30), 30, id="b-fully-inside-a"),
            pytest.param(time(18, 30), 30, time(18, 0), 120, id="a-fully-inside-b"),
            pytest.param(time(18, 0), 90, time(18, 0), 30, id="same-start-different-duration"),
            pytest.param(time(18, 0), 90, time(19, 29), 30, id="b-starts-one-minute-before-a-ends"),
            pytest.param(time(19, 29), 30, time(18, 0), 90, id="a-starts-one-minute-before-b-ends"),
            pytest.param(time(18, 0), 1, time(18, 0), 1, id="one-minute-slots-identical"),
        ],
    )
    def test_overlapping_slots(self, start_a, dur_a, start_b, dur_b):
        assert overlaps(start_a, dur_a, start_b, dur_b) is True

    @pytest.mark.parametrize(
        "start_a, dur_a, start_b, dur_b",
        [
            pytest.param(time(18, 0), 90, time(19, 30), 60, id="b-starts-exactly-when-a-ends"),
            pytest.param(time(19, 30), 60, time(18, 0), 90, id="a-starts-exactly-when-b-ends"),
            pytest.param(time(18, 0), 90, time(19, 31), 60, id="b-starts-one-minute-after-a-ends"),
            pytest.param(time(19, 31), 60, time(18, 0), 90, id="a-starts-one-minute-after-b-ends"),
            pytest.param(time(12, 0), 60, time(20, 0), 60, id="far-apart"),
            pytest.param(time(20, 0), 60, time(12, 0), 60, id="far-apart-reversed"),
            pytest.param(time(0, 0), 30, time(23, 30), 30, id="start-and-end-of-day"),
        ],
    )
    def test_non_overlapping_slots(self, start_a, dur_a, start_b, dur_b):
        assert overlaps(start_a, dur_a, start_b, dur_b) is False

    @pytest.mark.parametrize(
        "start_a, dur_a, start_b, dur_b",
        [
            (time(18, 0), 90, time(18, 30), 90),
            (time(18, 0), 90, time(19, 30), 60),
            (time(18, 0), 120, time(18, 30), 30),
            (time(10, 0), 60, time(20, 0), 60),
        ],
    )
    def test_is_symmetric(self, start_a, dur_a, start_b, dur_b):
        assert overlaps(start_a, dur_a, start_b, dur_b) == overlaps(start_b, dur_b, start_a, dur_a)

    def test_zero_duration_at_start_of_other_slot_does_not_overlap(self):
        # a zero-length slot occupies no time, so it cannot collide at the exact start of another slot
        assert overlaps(time(18, 0), 0, time(18, 0), 90) is False

    def test_zero_duration_strictly_inside_slot_overlaps(self):
        assert overlaps(time(18, 30), 0, time(18, 0), 90) is True

    def test_two_zero_duration_slots_never_overlap(self):
        assert overlaps(time(18, 0), 0, time(18, 0), 0) is False


class TestWithinOpeningHours:
    OPENING = time(11, 0)
    CLOSING = time(23, 0)

    def check(self, start: time, duration: int) -> bool:
        return within_opening_hours(start, duration, self.OPENING, self.CLOSING)

    @pytest.mark.parametrize(
        "start, duration",
        [
            pytest.param(time(18, 0), 90, id="middle-of-the-day"),
            pytest.param(time(11, 0), 60, id="starts-exactly-at-opening"),
            pytest.param(time(21, 30), 90, id="ends-exactly-at-closing"),
            pytest.param(time(11, 0), 720, id="fills-the-whole-opening-window"),
            pytest.param(time(22, 59), 1, id="last-possible-minute"),
            pytest.param(time(11, 0), 0, id="zero-duration-at-opening"),
            pytest.param(time(23, 0), 0, id="zero-duration-at-closing"),
        ],
    )
    def test_inside_opening_hours(self, start, duration):
        assert self.check(start, duration) is True

    @pytest.mark.parametrize(
        "start, duration",
        [
            pytest.param(time(10, 59), 60, id="starts-one-minute-before-opening"),
            pytest.param(time(3, 0), 60, id="starts-in-the-night"),
            pytest.param(time(21, 31), 90, id="ends-one-minute-after-closing"),
            pytest.param(time(22, 30), 60, id="ends-half-hour-after-closing"),
            pytest.param(time(23, 0), 30, id="starts-at-closing"),
            pytest.param(time(23, 30), 30, id="starts-after-closing"),
            pytest.param(time(11, 0), 721, id="longer-than-opening-window"),
            pytest.param(time(10, 0), 1440, id="spans-whole-day"),
        ],
    )
    def test_outside_opening_hours(self, start, duration):
        assert self.check(start, duration) is False

    def test_start_before_opening_is_rejected_even_if_it_ends_inside_opening_hours(self):
        # 09:00 + 180 min ends at 12:00, which is inside opening hours, but the start is not
        assert self.check(time(9, 0), 180) is False

    def test_works_with_other_opening_hours(self):
        assert within_opening_hours(time(6, 0), 60, time(6, 0), time(14, 0)) is True
        assert within_opening_hours(time(13, 30), 60, time(6, 0), time(14, 0)) is False
        assert within_opening_hours(time(5, 59), 30, time(6, 0), time(14, 0)) is False


class TestTableAllocator:
    @pytest.fixture
    def allocator(self):
        return TableAllocator()

    def test_no_tables(self, allocator):
        assert allocator.find_best_table([], 2, set()) is None

    def test_all_tables_too_small(self, allocator):
        tables = [make_table(1, seats=2), make_table(2, seats=4)]

        assert allocator.find_best_table(tables, 5, set()) is None

    def test_all_suitable_tables_are_busy(self, allocator):
        tables = [make_table(1, seats=4), make_table(2, seats=6)]

        assert allocator.find_best_table(tables, 3, {1, 2}) is None

    def test_free_tables_too_small_and_big_ones_busy(self, allocator):
        small, big = make_table(1, seats=2), make_table(2, seats=8)

        assert allocator.find_best_table([small, big], 4, {big.id}) is None

    def test_single_fitting_table(self, allocator):
        table = make_table(1, seats=4)

        assert allocator.find_best_table([table], 2, set()) is table

    def test_exact_fit_is_allowed(self, allocator):
        table = make_table(1, seats=4)

        assert allocator.find_best_table([table], 4, set()) is table

    def test_one_seat_too_few_is_rejected(self, allocator):
        assert allocator.find_best_table([make_table(1, seats=4)], 5, set()) is None

    def test_prefers_table_with_fewest_seats(self, allocator):
        small, medium, large = make_table(1, 2, 1), make_table(2, 4, 2), make_table(3, 8, 3)

        assert allocator.find_best_table([large, medium, small], 1, set()) is small
        assert allocator.find_best_table([large, medium, small], 3, set()) is medium
        assert allocator.find_best_table([large, medium, small], 5, set()) is large

    def test_tie_on_seats_prefers_lowest_table_number(self, allocator):
        t3, t1, t2 = make_table(30, 4, number=3), make_table(10, 4, number=1), make_table(20, 4, number=2)

        assert allocator.find_best_table([t3, t1, t2], 2, set()) is t1

    def test_seats_take_priority_over_table_number(self, allocator):
        low_number_big = make_table(1, seats=6, number=1)
        high_number_small = make_table(2, seats=2, number=9)

        assert allocator.find_best_table([low_number_big, high_number_small], 2, set()) is high_number_small

    def test_tie_break_uses_number_not_id(self, allocator):
        low_id_high_number = make_table(1, seats=4, number=5)
        high_id_low_number = make_table(99, seats=4, number=2)

        assert allocator.find_best_table([low_id_high_number, high_id_low_number], 2, set()) is high_id_low_number

    def test_busy_best_table_falls_back_to_next_best(self, allocator):
        best, second = make_table(1, seats=2, number=1), make_table(2, seats=4, number=2)

        assert allocator.find_best_table([best, second], 2, {best.id}) is second

    def test_busy_tie_winner_falls_back_to_other_tied_table(self, allocator):
        first, second = make_table(1, 4, number=1), make_table(2, 4, number=2)

        assert allocator.find_best_table([first, second], 2, {first.id}) is second

    def test_unrelated_busy_ids_are_ignored(self, allocator):
        table = make_table(1, seats=4)

        assert allocator.find_best_table([table], 2, {99, 100}) is table

    def test_result_does_not_depend_on_input_order(self, allocator):
        tables = [make_table(1, 6, 1), make_table(2, 2, 2), make_table(3, 4, 3), make_table(4, 2, 1)]

        forward = allocator.find_best_table(tables, 2, set())
        backward = allocator.find_best_table(list(reversed(tables)), 2, set())

        assert forward is backward
        assert forward.id == 4

    def test_accepts_any_iterable(self, allocator):
        tables = (make_table(i, seats=i * 2, number=i) for i in range(1, 4))

        result = allocator.find_best_table(tables, 3, set())

        assert result.id == 2

    def test_does_not_modify_its_inputs(self, allocator):
        tables = [make_table(2, 4, 2), make_table(1, 2, 1)]
        busy = {1}

        allocator.find_best_table(tables, 2, busy)

        assert [t.id for t in tables] == [2, 1]
        assert busy == {1}

    def test_party_size_zero_picks_smallest_table(self, allocator):
        small, big = make_table(1, seats=2), make_table(2, seats=8)

        assert allocator.find_best_table([big, small], 0, set()) is small
