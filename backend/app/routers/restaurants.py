from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Restaurant
from ..repositories import RestaurantRepository
from ..schemas import RestaurantIn, RestaurantOut

router = APIRouter(prefix="/restaurants", tags=["restaurants"])


def _validate(data: RestaurantIn) -> None:
    if data.opening_time >= data.closing_time:
        raise HTTPException(422, "Opening time must be before closing time")


@router.get("", response_model=list[RestaurantOut])
def list_restaurants(db: Session = Depends(get_db)):
    return RestaurantRepository(db).list()


@router.get("/{id}", response_model=RestaurantOut)
def get_restaurant(id: int, db: Session = Depends(get_db)):
    entity = RestaurantRepository(db).get(id)
    if entity is None:
        raise HTTPException(404, "Restaurant not found")
    return entity


@router.post("", response_model=RestaurantOut, status_code=201)
def create_restaurant(data: RestaurantIn, db: Session = Depends(get_db)):
    _validate(data)
    return RestaurantRepository(db).add(Restaurant(**data.model_dump()))


@router.put("/{id}", response_model=RestaurantOut)
def update_restaurant(id: int, data: RestaurantIn, db: Session = Depends(get_db)):
    _validate(data)
    repo = RestaurantRepository(db)
    entity = repo.get(id)
    if entity is None:
        raise HTTPException(404, "Restaurant not found")
    for key, value in data.model_dump().items():
        setattr(entity, key, value)
    repo.save()
    return entity


@router.delete("/{id}", status_code=204)
def delete_restaurant(id: int, db: Session = Depends(get_db)):
    repo = RestaurantRepository(db)
    entity = repo.get(id)
    if entity is None:
        raise HTTPException(404, "Restaurant not found")
    repo.delete(entity)
    return Response(status_code=204)
