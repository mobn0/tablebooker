"""Repositories encapsulate all DB access. Services depend on these (mockable)."""
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import DiningTable, Guest, Reservation, ReservationStatus, Restaurant


class RestaurantRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Restaurant | None:
        return self.db.get(Restaurant, id)

    def list(self) -> list[Restaurant]:
        return list(self.db.scalars(select(Restaurant).order_by(Restaurant.name)))

    def add(self, entity: Restaurant) -> Restaurant:
        self.db.add(entity)
        self.db.commit()
        return entity

    def save(self) -> None:
        self.db.commit()

    def delete(self, entity: Restaurant) -> None:
        self.db.delete(entity)
        self.db.commit()


class TableRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> DiningTable | None:
        return self.db.get(DiningTable, id)

    def list_for_restaurant(self, restaurant_id: int) -> list[DiningTable]:
        stmt = (
            select(DiningTable)
            .where(DiningTable.restaurant_id == restaurant_id)
            .order_by(DiningTable.number)
        )
        return list(self.db.scalars(stmt))

    def list(self) -> list[DiningTable]:
        return list(self.db.scalars(select(DiningTable).order_by(DiningTable.restaurant_id, DiningTable.number)))

    def add(self, entity: DiningTable) -> DiningTable:
        self.db.add(entity)
        self.db.commit()
        return entity

    def save(self) -> None:
        self.db.commit()

    def delete(self, entity: DiningTable) -> None:
        self.db.delete(entity)
        self.db.commit()


class GuestRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Guest | None:
        return self.db.get(Guest, id)

    def list(self) -> list[Guest]:
        return list(self.db.scalars(select(Guest).order_by(Guest.last_name, Guest.first_name)))

    def add(self, entity: Guest) -> Guest:
        self.db.add(entity)
        self.db.commit()
        return entity

    def save(self) -> None:
        self.db.commit()

    def delete(self, entity: Guest) -> None:
        self.db.delete(entity)
        self.db.commit()


class ReservationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, id: int) -> Reservation | None:
        return self.db.get(Reservation, id)

    def list_for_day(self, restaurant_id: int | None, day: date) -> list[Reservation]:
        stmt = select(Reservation).where(Reservation.date == day)
        if restaurant_id is not None:
            stmt = stmt.join(DiningTable).where(DiningTable.restaurant_id == restaurant_id)
        return list(self.db.scalars(stmt.order_by(Reservation.start_time)))

    def list_for_guest(self, guest_id: int) -> list[Reservation]:
        stmt = (
            select(Reservation)
            .where(Reservation.guest_id == guest_id)
            .order_by(Reservation.date.desc(), Reservation.start_time.desc())
        )
        return list(self.db.scalars(stmt))

    def list_active_for_table_and_day(self, table_id: int, day: date) -> list[Reservation]:
        stmt = select(Reservation).where(
            Reservation.table_id == table_id,
            Reservation.date == day,
            Reservation.status == ReservationStatus.BOOKED,
        )
        return list(self.db.scalars(stmt))

    def add(self, entity: Reservation) -> Reservation:
        self.db.add(entity)
        self.db.commit()
        return entity

    def save(self) -> None:
        self.db.commit()

    def delete(self, entity: Reservation) -> None:
        self.db.delete(entity)
        self.db.commit()
