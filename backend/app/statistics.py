"""Statistics calculated from the reservation data."""
from datetime import date

from .repositories import ReservationRepository, RestaurantRepository, TableRepository


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
        raise NotImplementedError
