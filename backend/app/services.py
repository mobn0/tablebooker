"""Business logic for reservations. All dependencies are injected (mockable)."""
from datetime import date, datetime, time

from .models import DiningTable, Reservation, ReservationStatus
from .repositories import (
    GuestRepository,
    ReservationRepository,
    RestaurantRepository,
    TableRepository,
)
from .scheduling import TableAllocator, overlaps, within_opening_hours


class DomainError(Exception):
    """Base class for business rule violations."""


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class ValidationError(DomainError):
    pass


class ReservationService:
    def __init__(
        self,
        reservations: ReservationRepository,
        tables: TableRepository,
        guests: GuestRepository,
        restaurants: RestaurantRepository,
        allocator: TableAllocator | None = None,
    ):
        self.reservations = reservations
        self.tables = tables
        self.guests = guests
        self.restaurants = restaurants
        self.allocator = allocator or TableAllocator()

    def reserve(
        self,
        guest_id: int,
        restaurant_id: int,
        day: date,
        start: time,
        party_size: int,
        duration_minutes: int = 90,
        table_id: int | None = None,
        now: datetime | None = None,
    ) -> Reservation:
        now = now or datetime.now()

        if self.guests.get(guest_id) is None:
            raise NotFoundError("Guest not found")
        restaurant = self.restaurants.get(restaurant_id)
        if restaurant is None:
            raise NotFoundError("Restaurant not found")

        if datetime.combine(day, start) < now:
            raise ValidationError("Reservation cannot be in the past")
        if not within_opening_hours(start, duration_minutes, restaurant.opening_time, restaurant.closing_time):
            raise ValidationError("Reservation must be within opening hours")

        restaurant_tables = self.tables.list_for_restaurant(restaurant_id)

        if table_id is not None:
            table = self._pick_requested_table(table_id, restaurant_id, party_size)
            if self._is_busy(table.id, day, start, duration_minutes):
                raise ConflictError("Table is already booked for this time slot")
        else:
            busy = {
                t.id for t in restaurant_tables if self._is_busy(t.id, day, start, duration_minutes)
            }
            table = self.allocator.find_best_table(restaurant_tables, party_size, busy)
            if table is None:
                raise ConflictError("No free table available for this party size and time")

        reservation = Reservation(
            guest_id=guest_id,
            table_id=table.id,
            date=day,
            start_time=start,
            duration_minutes=duration_minutes,
            party_size=party_size,
            status=ReservationStatus.BOOKED,
        )
        return self.reservations.add(reservation)

    def cancel(self, reservation_id: int) -> Reservation:
        return self._transition(reservation_id, ReservationStatus.CANCELLED)

    def complete(self, reservation_id: int) -> Reservation:
        return self._transition(reservation_id, ReservationStatus.COMPLETED)

    def mark_no_show(self, reservation_id: int) -> Reservation:
        return self._transition(reservation_id, ReservationStatus.NO_SHOW)

    # --- helpers -----------------------------------------------------

    def _transition(self, reservation_id: int, new_status: ReservationStatus) -> Reservation:
        reservation = self.reservations.get(reservation_id)
        if reservation is None:
            raise NotFoundError("Reservation not found")
        if reservation.status != ReservationStatus.BOOKED:
            raise ConflictError(f"Reservation is already {reservation.status.value}")
        reservation.status = new_status
        self.reservations.save()
        return reservation

    def _pick_requested_table(self, table_id: int, restaurant_id: int, party_size: int) -> DiningTable:
        table = self.tables.get(table_id)
        if table is None or table.restaurant_id != restaurant_id:
            raise NotFoundError("Table not found in this restaurant")
        if party_size > table.seats:
            raise ValidationError("Party size exceeds the number of seats at this table")
        return table

    def _is_busy(self, table_id: int, day: date, start: time, duration: int) -> bool:
        existing = self.reservations.list_active_for_table_and_day(table_id, day)
        return any(overlaps(start, duration, r.start_time, r.duration_minutes) for r in existing)
