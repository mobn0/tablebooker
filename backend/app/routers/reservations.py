from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_reservation_service
from ..models import Reservation
from ..repositories import ReservationRepository
from ..schemas import ReservationIn, ReservationOut
from ..services import ConflictError, DomainError, NotFoundError, ReservationService

router = APIRouter(prefix="/reservations", tags=["reservations"])


def to_out(r: Reservation) -> ReservationOut:
    return ReservationOut(
        id=r.id,
        guest_id=r.guest_id,
        table_id=r.table_id,
        date=r.date,
        start_time=r.start_time,
        duration_minutes=r.duration_minutes,
        party_size=r.party_size,
        status=r.status,
        guest_name=f"{r.guest.first_name} {r.guest.last_name}",
        table_number=r.table.number,
        restaurant_id=r.table.restaurant_id,
    )


def http_error(e: DomainError) -> HTTPException:
    if isinstance(e, NotFoundError):
        return HTTPException(404, str(e))
    if isinstance(e, ConflictError):
        return HTTPException(409, str(e))
    return HTTPException(422, str(e))


@router.get("", response_model=list[ReservationOut])
def list_reservations(
    day: date, restaurant_id: int | None = None, db: Session = Depends(get_db)
):
    """Daily reservation list, optionally for one restaurant."""
    return [to_out(r) for r in ReservationRepository(db).list_for_day(restaurant_id, day)]


@router.get("/by-guest/{guest_id}", response_model=list[ReservationOut])
def guest_history(guest_id: int, db: Session = Depends(get_db)):
    return [to_out(r) for r in ReservationRepository(db).list_for_guest(guest_id)]


@router.post("", response_model=ReservationOut, status_code=201)
def create_reservation(
    data: ReservationIn, service: ReservationService = Depends(get_reservation_service)
):
    try:
        reservation = service.reserve(
            guest_id=data.guest_id,
            restaurant_id=data.restaurant_id,
            day=data.date,
            start=data.start_time,
            party_size=data.party_size,
            duration_minutes=data.duration_minutes,
            table_id=data.table_id,
        )
    except DomainError as e:
        raise http_error(e)
    return to_out(reservation)


@router.post("/{id}/cancel", response_model=ReservationOut)
def cancel(id: int, service: ReservationService = Depends(get_reservation_service)):
    try:
        return to_out(service.cancel(id))
    except DomainError as e:
        raise http_error(e)


@router.post("/{id}/complete", response_model=ReservationOut)
def complete(id: int, service: ReservationService = Depends(get_reservation_service)):
    try:
        return to_out(service.complete(id))
    except DomainError as e:
        raise http_error(e)


@router.post("/{id}/no-show", response_model=ReservationOut)
def no_show(id: int, service: ReservationService = Depends(get_reservation_service)):
    try:
        return to_out(service.mark_no_show(id))
    except DomainError as e:
        raise http_error(e)
