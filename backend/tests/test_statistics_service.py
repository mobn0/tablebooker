"""Unit tests for StatisticsService.occupancy_rate (written test-first, TDD).

occupancy_rate = booked minutes / (number of tables x opening minutes), as a float 0..1.
Only reservations with status BOOKED count. All repositories are mocked (no DB).
"""
from datetime import date, time
from unittest.mock import Mock

import pytest

from app.models import DiningTable, Reservation, ReservationStatus, Restaurant
from app.repositories import ReservationRepository, RestaurantRepository, TableRepository
from app.services import NotFoundError
from app.statistics import StatisticsService

RESTAURANT_ID = 3
DAY = date(2030, 6, 16)
OPENING = time(10, 0)
CLOSING = time(22, 0)  # 12 h = 720 opening minutes
OPENING_MINUTES = 720


def make_restaurant(opening: time = OPENING, closing: time = CLOSING) -> Restaurant:
    return Restaurant(id=RESTAURANT_ID, name="Chez Test", opening_time=opening, closing_time=closing)


def make_tables(count: int) -> list[DiningTable]:
    return [
        DiningTable(id=100 + n, restaurant_id=RESTAURANT_ID, number=n, seats=4)
        for n in range(1, count + 1)
    ]


def make_reservation(
    duration: int = 90,
    status: ReservationStatus = ReservationStatus.BOOKED,
    start: time = time(18, 0),
) -> Reservation:
    return Reservation(
        guest_id=7,
        table_id=101,
        date=DAY,
        start_time=start,
        duration_minutes=duration,
        party_size=2,
        status=status,
    )


@pytest.fixture
def reservations():
    repo = Mock(spec=ReservationRepository)
    repo.list_for_day.return_value = []
    return repo


@pytest.fixture
def tables():
    repo = Mock(spec=TableRepository)
    repo.list_for_restaurant.return_value = make_tables(2)
    return repo


@pytest.fixture
def restaurants():
    repo = Mock(spec=RestaurantRepository)
    repo.get.return_value = make_restaurant()
    return repo


@pytest.fixture
def service(reservations, tables, restaurants):
    return StatisticsService(reservations, tables, restaurants)


def test_no_reservations_gives_zero(service):
    assert service.occupancy_rate(RESTAURANT_ID, DAY) == 0.0


def test_one_reservation_exact_value(service, reservations):
    # 2 tables x 720 min = 1440 table-minutes; 90 / 1440 = 0.0625
    reservations.list_for_day.return_value = [make_reservation(duration=90)]

    assert service.occupancy_rate(RESTAURANT_ID, DAY) == 0.0625


def test_several_reservations_are_summed(service, reservations):
    # (90 + 120 + 30) / 1440 = 240 / 1440 = 1/6
    reservations.list_for_day.return_value = [
        make_reservation(duration=90),
        make_reservation(duration=120, start=time(12, 0)),
        make_reservation(duration=30, start=time(15, 0)),
    ]

    assert service.occupancy_rate(RESTAURANT_ID, DAY) == pytest.approx(240 / 1440)


def test_fully_booked_day_gives_one(service, reservations):
    # every table booked for the complete opening time
    reservations.list_for_day.return_value = [
        make_reservation(duration=OPENING_MINUTES, start=OPENING),
        make_reservation(duration=OPENING_MINUTES, start=OPENING),
    ]

    assert service.occupancy_rate(RESTAURANT_ID, DAY) == 1.0


@pytest.mark.parametrize(
    "status",
    [ReservationStatus.CANCELLED, ReservationStatus.COMPLETED, ReservationStatus.NO_SHOW],
)
def test_only_booked_reservations_count(service, reservations, status):
    reservations.list_for_day.return_value = [
        make_reservation(duration=90, status=ReservationStatus.BOOKED),
        make_reservation(duration=300, status=status),
    ]

    assert service.occupancy_rate(RESTAURANT_ID, DAY) == 0.0625


def test_only_non_booked_reservations_give_zero(service, reservations):
    reservations.list_for_day.return_value = [
        make_reservation(status=ReservationStatus.CANCELLED),
        make_reservation(status=ReservationStatus.COMPLETED),
        make_reservation(status=ReservationStatus.NO_SHOW),
    ]

    assert service.occupancy_rate(RESTAURANT_ID, DAY) == 0.0


def test_capacity_depends_on_number_of_tables(service, reservations, tables):
    # 4 tables x 720 min = 2880 table-minutes; 90 / 2880 = 0.03125
    tables.list_for_restaurant.return_value = make_tables(4)
    reservations.list_for_day.return_value = [make_reservation(duration=90)]

    assert service.occupancy_rate(RESTAURANT_ID, DAY) == 0.03125


def test_capacity_depends_on_opening_hours(service, reservations, restaurants):
    # 2 tables x 360 min (10:00-16:00) = 720 table-minutes; 90 / 720 = 0.125
    restaurants.get.return_value = make_restaurant(opening=time(10, 0), closing=time(16, 0))
    reservations.list_for_day.return_value = [make_reservation(duration=90)]

    assert service.occupancy_rate(RESTAURANT_ID, DAY) == 0.125


def test_opening_time_with_minutes_is_respected(service, reservations, restaurants):
    # 2 tables x 450 min (10:30-18:00) = 900 table-minutes; 90 / 900 = 0.1
    restaurants.get.return_value = make_restaurant(opening=time(10, 30), closing=time(18, 0))
    reservations.list_for_day.return_value = [make_reservation(duration=90)]

    assert service.occupancy_rate(RESTAURANT_ID, DAY) == pytest.approx(0.1)


def test_unknown_restaurant_raises_not_found(service, restaurants):
    restaurants.get.return_value = None

    with pytest.raises(NotFoundError):
        service.occupancy_rate(999, DAY)


def test_unknown_restaurant_does_not_query_reservations_or_tables(
    service, restaurants, reservations, tables
):
    restaurants.get.return_value = None

    with pytest.raises(NotFoundError):
        service.occupancy_rate(999, DAY)

    reservations.list_for_day.assert_not_called()
    tables.list_for_restaurant.assert_not_called()


def test_restaurant_without_tables_gives_zero(service, tables):
    tables.list_for_restaurant.return_value = []

    assert service.occupancy_rate(RESTAURANT_ID, DAY) == 0.0


def test_restaurant_with_zero_opening_minutes_gives_zero(service, reservations, restaurants):
    restaurants.get.return_value = make_restaurant(opening=time(12, 0), closing=time(12, 0))
    reservations.list_for_day.return_value = [make_reservation()]

    assert service.occupancy_rate(RESTAURANT_ID, DAY) == 0.0


def test_repositories_are_queried_for_the_given_restaurant_and_day(
    service, restaurants, reservations, tables
):
    service.occupancy_rate(RESTAURANT_ID, DAY)

    restaurants.get.assert_called_once_with(RESTAURANT_ID)
    tables.list_for_restaurant.assert_called_once_with(RESTAURANT_ID)
    reservations.list_for_day.assert_called_once_with(RESTAURANT_ID, DAY)
