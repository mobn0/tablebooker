from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field

from .models import ReservationStatus


class RestaurantIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    address: str = ""
    opening_time: time
    closing_time: time


class RestaurantOut(RestaurantIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class TableIn(BaseModel):
    restaurant_id: int
    number: int = Field(ge=1)
    seats: int = Field(ge=1, le=30)
    location: str = "inside"


class TableOut(TableIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class GuestIn(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: str = ""
    phone: str = ""


class GuestOut(GuestIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ReservationIn(BaseModel):
    guest_id: int
    restaurant_id: int
    date: date
    start_time: time
    party_size: int = Field(ge=1, le=30)
    duration_minutes: int = Field(default=90, ge=15, le=480)
    table_id: int | None = None  # None -> best-fitting table is chosen automatically


class ReservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    guest_id: int
    table_id: int
    date: date
    start_time: time
    duration_minutes: int
    party_size: int
    status: ReservationStatus
    guest_name: str = ""
    table_number: int = 0
    restaurant_id: int = 0
