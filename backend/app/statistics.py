"""Statistics calculated from the reservation data."""
from datetime import date

from .models import ReservationStatus
from .repositories import ReservationRepository, RestaurantRepository, TableRepository
from .scheduling import to_minutes
from .services import NotFoundError


class StatisticsService:
    def __init__(
        self,
        reservations: ReservationRepository,
        tables: TableRepository,
        restaurants: RestaurantRepository,
    ):
        self.reservations = reservations
        self.tables = tables
        self.restaurants = restaurants

    def occupancy_rate(self, restaurant_id: int, day: date) -> float:
        """Share (0..1) of the available table-minutes that are booked on the given day.

        booked minutes (status BOOKED only) / (number of tables x opening minutes)
        """
        restaurant = self.restaurants.get(restaurant_id)
        if restaurant is None:
            raise NotFoundError("Restaurant not found")

        table_count = len(self.tables.list_for_restaurant(restaurant_id))
        opening_minutes = to_minutes(restaurant.closing_time) - to_minutes(restaurant.opening_time)
        capacity = table_count * opening_minutes
        if capacity <= 0:
            return 0.0

        booked_minutes = sum(
            r.duration_minutes
            for r in self.reservations.list_for_day(restaurant_id, day)
            if r.status == ReservationStatus.BOOKED
        )
        return booked_minutes / capacity
