import os
from contextlib import asynccontextmanager
from datetime import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import Base, SessionLocal, engine
from .routers import guests, reservations, restaurants, tables


def seed(db) -> None:
    """Insert demo data on first start."""
    if db.query(models.Restaurant).count() > 0:
        return
    restaurant = models.Restaurant(
        name="Zum Goldenen Fass",
        address="Marktplatz 1, 4051 Basel",
        opening_time=time(11, 0),
        closing_time=time(23, 0),
    )
    db.add(restaurant)
    db.flush()
    for number, seats, location in [(1, 2, "inside"), (2, 2, "inside"), (3, 4, "inside"),
                                    (4, 4, "terrace"), (5, 6, "inside"), (6, 8, "terrace")]:
        db.add(models.DiningTable(restaurant_id=restaurant.id, number=number, seats=seats, location=location))
    db.add(models.Guest(first_name="Anna", last_name="Meier", email="anna@example.ch", phone="+41 61 000 00 01"))
    db.add(models.Guest(first_name="Luca", last_name="Rossi", email="luca@example.ch", phone="+41 61 000 00 02"))
    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs("data", exist_ok=True)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(title="TableBooker API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

for r in (restaurants.router, tables.router, guests.router, reservations.router):
    app.include_router(r, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok"}
