from fastapi import Depends
from sqlalchemy.orm import Session

from .database import get_db
from .repositories import (
    GuestRepository,
    ReservationRepository,
    RestaurantRepository,
    TableRepository,
)
from .services import ReservationService


def get_reservation_service(db: Session = Depends(get_db)) -> ReservationService:
    return ReservationService(
        ReservationRepository(db),
        TableRepository(db),
        GuestRepository(db),
        RestaurantRepository(db),
    )
