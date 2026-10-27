from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Guest
from ..repositories import GuestRepository
from ..schemas import GuestIn, GuestOut

router = APIRouter(prefix="/guests", tags=["guests"])


@router.get("", response_model=list[GuestOut])
def list_guests(db: Session = Depends(get_db)):
    return GuestRepository(db).list()


@router.post("", response_model=GuestOut, status_code=201)
def create_guest(data: GuestIn, db: Session = Depends(get_db)):
    return GuestRepository(db).add(Guest(**data.model_dump()))


@router.put("/{id}", response_model=GuestOut)
def update_guest(id: int, data: GuestIn, db: Session = Depends(get_db)):
    repo = GuestRepository(db)
    entity = repo.get(id)
    if entity is None:
        raise HTTPException(404, "Guest not found")
    for key, value in data.model_dump().items():
        setattr(entity, key, value)
    repo.save()
    return entity


@router.delete("/{id}", status_code=204)
def delete_guest(id: int, db: Session = Depends(get_db)):
    repo = GuestRepository(db)
    entity = repo.get(id)
    if entity is None:
        raise HTTPException(404, "Guest not found")
    repo.delete(entity)
    return Response(status_code=204)
