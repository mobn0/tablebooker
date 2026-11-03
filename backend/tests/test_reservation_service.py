from datetime import date, datetime, time
from unittest.mock import Mock, call

import pytest

from app.models import DiningTable, Guest, Reservation, ReservationStatus, Restaurant
from app.repositories import (
    GuestRepository,
    ReservationRepository,
    RestaurantRepository,
    TableRepository,
)
from app.scheduling import TableAllocator
from app.services import (
    ConflictError,
    NotFoundError,
    ReservationService,
    ValidationError,
)

GUEST_ID = 7
RESTAURANT_ID = 3
TABLE_ID = 11
RESERVATION_ID = 42

NOW = datetime(2030, 6, 15, 12, 0)
DAY = date(2030, 6, 16)
START = time(18, 0)
OPENING = time(11, 0)
CLOSING = time(23, 0)


def make_restaurant() -> Restaurant:
    return Restaurant(id=RESTAURANT_ID, name="Chez Test", opening_time=OPENING, closing_time=CLOSING)


def make_table(id: int = TABLE_ID, seats: int = 4, number: int = 1, restaurant_id: int = RESTAURANT_ID) -> DiningTable:
    return DiningTable(id=id, restaurant_id=restaurant_id, number=number, seats=seats)


def make_reservation(
    status: ReservationStatus = ReservationStatus.BOOKED,
    start: time = START,
    duration: int = 90,
) -> Reservation:
    return Reservation(
        id=RESERVATION_ID,
        guest_id=GUEST_ID,
        table_id=TABLE_ID,
        date=DAY,
        start_time=start,
        duration_minutes=duration,
        party_size=2,
        status=status,
    )


@pytest.fixture
def reservations():
    repo = Mock(spec=ReservationRepository)
    repo.list_active_for_table_and_day.return_value = []
    return repo


@pytest.fixture
def tables():
    return Mock(spec=TableRepository)


@pytest.fixture
def guests():
    repo = Mock(spec=GuestRepository)
    repo.get.return_value = Guest(id=GUEST_ID, first_name="Max", last_name="Muster")
    return repo


@pytest.fixture
def restaurants():
    repo = Mock(spec=RestaurantRepository)
    repo.get.return_value = make_restaurant()
    return repo


@pytest.fixture
def allocator():
    return Mock(spec=TableAllocator)


@pytest.fixture
def service(reservations, tables, guests, restaurants, allocator):
    return ReservationService(reservations, tables, guests, restaurants, allocator)


def reserve(service: ReservationService, **overrides) -> Reservation:
    kwargs = dict(
        guest_id=GUEST_ID,
        restaurant_id=RESTAURANT_ID,
        day=DAY,
        start=START,
        party_size=2,
        now=NOW,
    )
    kwargs.update(overrides)
    return service.reserve(**kwargs)


class TestReserve:
    def test_guest_not_found(self, service, reservations, tables, guests, restaurants):
        guests.get.return_value = None

        with pytest.raises(NotFoundError, match=r"^Guest not found$"):
            reserve(service)

        guests.get.assert_called_once_with(GUEST_ID)
        restaurants.get.assert_not_called()
        tables.list_for_restaurant.assert_not_called()
        reservations.add.assert_not_called()

    def test_restaurant_not_found(self, service, reservations, tables, guests, restaurants):
        restaurants.get.return_value = None

        with pytest.raises(NotFoundError, match=r"^Restaurant not found$"):
            reserve(service)

        guests.get.assert_called_once_with(GUEST_ID)
        restaurants.get.assert_called_once_with(RESTAURANT_ID)
        tables.list_for_restaurant.assert_not_called()
        reservations.add.assert_not_called()

    def test_start_in_the_past(self, service, reservations, tables):
        with pytest.raises(ValidationError, match=r"^Reservation cannot be in the past$"):
            reserve(service, day=NOW.date(), start=time(11, 59), table_id=TABLE_ID)

        tables.list_for_restaurant.assert_not_called()
        tables.get.assert_not_called()
        reservations.add.assert_not_called()

    def test_past_day_is_rejected_even_if_time_is_later(self, service, reservations):
        with pytest.raises(ValidationError, match=r"^Reservation cannot be in the past$"):
            reserve(service, day=date(2030, 6, 14), start=time(18, 0), table_id=TABLE_ID)

        reservations.add.assert_not_called()

    def test_past_check_comes_before_opening_hours_check(self, service, reservations):
        with pytest.raises(ValidationError, match=r"^Reservation cannot be in the past$"):
            reserve(service, day=date(2030, 6, 14), start=time(3, 0), table_id=TABLE_ID)

        reservations.add.assert_not_called()

    def test_start_equal_to_now_is_allowed(self, service, reservations, tables):
        tables.get.return_value = make_table()

        reserve(service, day=NOW.date(), start=NOW.time(), table_id=TABLE_ID)

        reservations.add.assert_called_once()

    def test_without_now_the_real_clock_is_used(self, service, reservations):
        with pytest.raises(ValidationError, match=r"^Reservation cannot be in the past$"):
            service.reserve(
                guest_id=GUEST_ID,
                restaurant_id=RESTAURANT_ID,
                day=date(2000, 1, 1),
                start=START,
                party_size=2,
                table_id=TABLE_ID,
            )

        reservations.add.assert_not_called()

    @pytest.mark.parametrize(
        "start, duration",
        [
            pytest.param(time(10, 59), 60, id="starts-one-minute-before-opening"),
            pytest.param(time(21, 31), 90, id="ends-one-minute-after-closing"),
            pytest.param(time(23, 0), 30, id="starts-at-closing"),
        ],
    )
    def test_outside_opening_hours(self, service, reservations, tables, start, duration):
        with pytest.raises(ValidationError, match=r"^Reservation must be within opening hours$"):
            reserve(service, start=start, duration_minutes=duration, table_id=TABLE_ID)

        tables.list_for_restaurant.assert_not_called()
        tables.get.assert_not_called()
        reservations.add.assert_not_called()

    @pytest.mark.parametrize(
        "start, duration",
        [
            pytest.param(time(11, 0), 60, id="starts-exactly-at-opening"),
            pytest.param(time(21, 30), 90, id="ends-exactly-at-closing"),
        ],
    )
    def test_opening_hours_boundaries_are_inclusive(self, service, reservations, tables, start, duration):
        tables.get.return_value = make_table()

        reserve(service, start=start, duration_minutes=duration, table_id=TABLE_ID)

        reservations.add.assert_called_once()

    def test_chosen_table_not_found(self, service, reservations, tables, allocator):
        tables.get.return_value = None

        with pytest.raises(NotFoundError, match=r"^Table not found in this restaurant$"):
            reserve(service, table_id=TABLE_ID)

        tables.get.assert_called_once_with(TABLE_ID)
        reservations.list_active_for_table_and_day.assert_not_called()
        allocator.find_best_table.assert_not_called()
        reservations.add.assert_not_called()

    def test_chosen_table_belongs_to_other_restaurant(self, service, reservations, tables, allocator):
        tables.get.return_value = make_table(restaurant_id=RESTAURANT_ID + 1)

        with pytest.raises(NotFoundError, match=r"^Table not found in this restaurant$"):
            reserve(service, table_id=TABLE_ID)

        tables.get.assert_called_once_with(TABLE_ID)
        reservations.list_active_for_table_and_day.assert_not_called()
        allocator.find_best_table.assert_not_called()
        reservations.add.assert_not_called()

    def test_chosen_table_too_small_for_party(self, service, reservations, tables, allocator):
        tables.get.return_value = make_table(seats=4)

        with pytest.raises(
            ValidationError,
            match=r"^Party size exceeds the number of seats at this table$",
        ):
            reserve(service, table_id=TABLE_ID, party_size=5)

        tables.get.assert_called_once_with(TABLE_ID)
        reservations.list_active_for_table_and_day.assert_not_called()
        allocator.find_best_table.assert_not_called()
        reservations.add.assert_not_called()

    def test_chosen_table_is_busy(self, service, reservations, tables, allocator):
        tables.get.return_value = make_table()
        reservations.list_active_for_table_and_day.return_value = [make_reservation(start=time(17, 30))]

        with pytest.raises(ConflictError, match=r"^Table is already booked for this time slot$"):
            reserve(service, table_id=TABLE_ID)

        reservations.list_active_for_table_and_day.assert_called_once_with(TABLE_ID, DAY)
        allocator.find_best_table.assert_not_called()
        reservations.add.assert_not_called()

    def test_chosen_table_directly_after_existing_reservation_is_free(self, service, reservations, tables):
        tables.get.return_value = make_table()
        reservations.list_active_for_table_and_day.return_value = [make_reservation(start=time(16, 30))]

        reserve(service, table_id=TABLE_ID)

        reservations.add.assert_called_once()

    def test_chosen_table_success(self, service, reservations, tables, allocator):
        tables.get.return_value = make_table(seats=4)

        result = reserve(service, table_id=TABLE_ID, party_size=4, duration_minutes=60)

        assert result is reservations.add.return_value
        tables.get.assert_called_once_with(TABLE_ID)
        tables.list_for_restaurant.assert_called_once_with(RESTAURANT_ID)
        reservations.list_active_for_table_and_day.assert_called_once_with(TABLE_ID, DAY)
        allocator.find_best_table.assert_not_called()
        reservations.add.assert_called_once()
        saved = reservations.add.call_args.args[0]
        assert isinstance(saved, Reservation)
        assert saved.guest_id == GUEST_ID
        assert saved.table_id == TABLE_ID
        assert saved.date == DAY
        assert saved.start_time == START
        assert saved.duration_minutes == 60
        assert saved.party_size == 4
        assert saved.status == ReservationStatus.BOOKED

    def test_default_duration_is_90_minutes(self, service, reservations, tables):
        tables.get.return_value = make_table()

        reserve(service, table_id=TABLE_ID)

        saved = reservations.add.call_args.args[0]
        assert saved.duration_minutes == 90

    def test_allocator_picks_the_table(self, service, reservations, tables, allocator):
        small, big = make_table(id=1, seats=2, number=1), make_table(id=2, seats=6, number=2)
        tables.list_for_restaurant.return_value = [small, big]
        allocator.find_best_table.return_value = big

        result = reserve(service, party_size=3)

        assert result is reservations.add.return_value
        tables.get.assert_not_called()
        tables.list_for_restaurant.assert_called_once_with(RESTAURANT_ID)
        allocator.find_best_table.assert_called_once_with([small, big], 3, set())
        reservations.add.assert_called_once()
        saved = reservations.add.call_args.args[0]
        assert saved.table_id == big.id
        assert saved.guest_id == GUEST_ID
        assert saved.party_size == 3
        assert saved.status == ReservationStatus.BOOKED

    def test_no_free_table_available(self, service, reservations, tables, allocator):
        tables.list_for_restaurant.return_value = [make_table(id=1, seats=2)]
        allocator.find_best_table.return_value = None

        with pytest.raises(
            ConflictError,
            match=r"^No free table available for this party size and time$",
        ):
            reserve(service, party_size=8)

        allocator.find_best_table.assert_called_once_with(tables.list_for_restaurant.return_value, 8, set())
        reservations.add.assert_not_called()

    def test_busy_tables_are_excluded_from_allocation(self, service, reservations, tables, allocator):
        busy_table, free_table = make_table(id=1, number=1), make_table(id=2, number=2)
        tables.list_for_restaurant.return_value = [busy_table, free_table]
        allocator.find_best_table.return_value = free_table

        def active_reservations(table_id, day):
            return [make_reservation(start=time(18, 30))] if table_id == busy_table.id else []

        reservations.list_active_for_table_and_day.side_effect = active_reservations

        reserve(service, party_size=2)

        assert reservations.list_active_for_table_and_day.call_args_list == [
            call(busy_table.id, DAY),
            call(free_table.id, DAY),
        ]
        allocator.find_best_table.assert_called_once_with([busy_table, free_table], 2, {busy_table.id})
        saved = reservations.add.call_args.args[0]
        assert saved.table_id == free_table.id

    def test_non_overlapping_tables_are_not_excluded(self, service, reservations, tables, allocator):
        table = make_table(id=1)
        tables.list_for_restaurant.return_value = [table]
        allocator.find_best_table.return_value = table
        reservations.list_active_for_table_and_day.return_value = [make_reservation(start=time(19, 30))]

        reserve(service)

        allocator.find_best_table.assert_called_once_with([table], 2, set())

    def test_default_allocator_is_created_when_none_given(self, reservations, tables, guests, restaurants):
        service = ReservationService(reservations, tables, guests, restaurants)

        assert isinstance(service.allocator, TableAllocator)


class TestCancel:
    def test_not_found(self, service, reservations):
        reservations.get.return_value = None

        with pytest.raises(NotFoundError, match=r"^Reservation not found$"):
            service.cancel(RESERVATION_ID)

        reservations.get.assert_called_once_with(RESERVATION_ID)
        reservations.save.assert_not_called()

    @pytest.mark.parametrize(
        "status, text",
        [
            pytest.param(ReservationStatus.CANCELLED, "cancelled", id="cancelled"),
            pytest.param(ReservationStatus.COMPLETED, "completed", id="completed"),
            pytest.param(ReservationStatus.NO_SHOW, "no_show", id="no_show"),
        ],
    )
    def test_status_not_booked(self, service, reservations, status, text):
        reservation = make_reservation(status=status)
        reservations.get.return_value = reservation

        with pytest.raises(ConflictError, match=rf"^Reservation is already {text}$"):
            service.cancel(RESERVATION_ID)

        reservations.get.assert_called_once_with(RESERVATION_ID)
        reservations.save.assert_not_called()
        assert reservation.status == status

    def test_success(self, service, reservations):
        reservation = make_reservation(status=ReservationStatus.BOOKED)
        reservations.get.return_value = reservation

        result = service.cancel(RESERVATION_ID)

        assert result is reservation
        assert reservation.status == ReservationStatus.CANCELLED
        reservations.get.assert_called_once_with(RESERVATION_ID)
        reservations.save.assert_called_once_with()


class TestComplete:
    def test_not_found(self, service, reservations):
        reservations.get.return_value = None

        with pytest.raises(NotFoundError, match=r"^Reservation not found$"):
            service.complete(RESERVATION_ID)

        reservations.get.assert_called_once_with(RESERVATION_ID)
        reservations.save.assert_not_called()

    @pytest.mark.parametrize(
        "status, text",
        [
            pytest.param(ReservationStatus.CANCELLED, "cancelled", id="cancelled"),
            pytest.param(ReservationStatus.COMPLETED, "completed", id="completed"),
            pytest.param(ReservationStatus.NO_SHOW, "no_show", id="no_show"),
        ],
    )
    def test_status_not_booked(self, service, reservations, status, text):
        reservation = make_reservation(status=status)
        reservations.get.return_value = reservation

        with pytest.raises(ConflictError, match=rf"^Reservation is already {text}$"):
            service.complete(RESERVATION_ID)

        reservations.get.assert_called_once_with(RESERVATION_ID)
        reservations.save.assert_not_called()
        assert reservation.status == status

    def test_success(self, service, reservations):
        reservation = make_reservation(status=ReservationStatus.BOOKED)
        reservations.get.return_value = reservation

        result = service.complete(RESERVATION_ID)

        assert result is reservation
        assert reservation.status == ReservationStatus.COMPLETED
        reservations.get.assert_called_once_with(RESERVATION_ID)
        reservations.save.assert_called_once_with()


class TestMarkNoShow:
    def test_not_found(self, service, reservations):
        reservations.get.return_value = None

        with pytest.raises(NotFoundError, match=r"^Reservation not found$"):
            service.mark_no_show(RESERVATION_ID)

        reservations.get.assert_called_once_with(RESERVATION_ID)
        reservations.save.assert_not_called()

    @pytest.mark.parametrize(
        "status, text",
        [
            pytest.param(ReservationStatus.CANCELLED, "cancelled", id="cancelled"),
            pytest.param(ReservationStatus.COMPLETED, "completed", id="completed"),
            pytest.param(ReservationStatus.NO_SHOW, "no_show", id="no_show"),
        ],
    )
    def test_status_not_booked(self, service, reservations, status, text):
        reservation = make_reservation(status=status)
        reservations.get.return_value = reservation

        with pytest.raises(ConflictError, match=rf"^Reservation is already {text}$"):
            service.mark_no_show(RESERVATION_ID)

        reservations.get.assert_called_once_with(RESERVATION_ID)
        reservations.save.assert_not_called()
        assert reservation.status == status

    def test_success(self, service, reservations):
        reservation = make_reservation(status=ReservationStatus.BOOKED)
        reservations.get.return_value = reservation

        result = service.mark_no_show(RESERVATION_ID)

        assert result is reservation
        assert reservation.status == ReservationStatus.NO_SHOW
        reservations.get.assert_called_once_with(RESERVATION_ID)
        reservations.save.assert_called_once_with()
