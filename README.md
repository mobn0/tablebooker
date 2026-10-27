# TableBooker – Restaurant Reservation System

FastAPI (Python) backend · SQLite · Angular frontend using the [newang](https://newang.noecore.com) component library.

## Run

    docker compose up --build

- App:      http://localhost:8080
- API docs: http://localhost:8000/docs (Swagger UI)

Demo data (1 restaurant, 6 tables, 2 guests) is inserted on first start.
The SQLite file lives in the `db-data` volume. Reset with `docker compose down -v`.

## Run without Docker

    # backend
    cd backend
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload          # http://localhost:8000

    # frontend (second terminal)
    cd frontend
    npm install
    npx ng serve --proxy-config proxy.conf.json   # http://localhost:4200

## Structure (built for testing)

    backend/app/
      models.py         SQLAlchemy entities: Restaurant, DiningTable, Guest, Reservation
      repositories.py   all DB access (mock these for unit tests, chapter 3.1)
      services.py       ReservationService: business rules, depends only on repositories
      scheduling.py     pure logic: overlaps(), within_opening_hours(), TableAllocator (chapter 3.2)
      routers/          REST endpoints (CRUD)
    backend/tests/      put your tests here

## Business rules

- No overlapping bookings for one table (touching slots like 18:00–19:30 and 19:30–21:00 are fine)
- Party size must not exceed the seats of the table
- Reservation must lie fully within opening hours
- Default duration 90 minutes
- No reservations in the past
- Cancelled / completed / no-show reservations free the table; only `booked` ones can change status
- Without a chosen table, the smallest free table that fits is picked (lowest number on ties)
