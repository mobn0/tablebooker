from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import DiningTable
from ..repositories import RestaurantRepository, TableRepository
from ..schemas import TableIn, TableOut

router = APIRouter(prefix="/tables", tags=["tables"])


@router.get("", response_model=list[TableOut])
def list_tables(restaurant_id: int | None = None, db: Session = Depends(get_db)):
    repo = TableRepository(db)
    return repo.list_for_restaurant(restaurant_id) if restaurant_id else repo.list()


@router.post("", response_model=TableOut, status_code=201)
def create_table(data: TableIn, db: Session = Depends(get_db)):
    if RestaurantRepository(db).get(data.restaurant_id) is None:
        raise HTTPException(404, "Restaurant not found")
    existing = TableRepository(db).list_for_restaurant(data.restaurant_id)
    if any(t.number == data.number for t in existing):
        raise HTTPException(409, "Table number already exists in this restaurant")
    return TableRepository(db).add(DiningTable(**data.model_dump()))


@router.put("/{id}", response_model=TableOut)
def update_table(id: int, data: TableIn, db: Session = Depends(get_db)):
    repo = TableRepository(db)
    entity = repo.get(id)
    if entity is None:
        raise HTTPException(404, "Table not found")
    for key, value in data.model_dump().items():
        setattr(entity, key, value)
    repo.save()
    return entity


@router.delete("/{id}", status_code=204)
def delete_table(id: int, db: Session = Depends(get_db)):
    repo = TableRepository(db)
    entity = repo.get(id)
    if entity is None:
        raise HTTPException(404, "Table not found")
    repo.delete(entity)
    return Response(status_code=204)
