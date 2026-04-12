# polymarket-weather-v1

Correlation engine between Polymarket prediction markets and weather data.

## Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# edit .env as needed

# 2. Start services
docker compose up -d --build

# 3. Verify
curl http://localhost:8000/health
# {"status":"ok","service":"polymarket-weather-v1"}
```

## Local Development (without Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# run migrations
alembic upgrade head

# start dev server
uvicorn app.main:app --reload
```

## Database Migrations

```bash
# generate a new migration
alembic revision --autogenerate -m "describe change"

# apply migrations
alembic upgrade head

# rollback one step
alembic downgrade -1
```

## Project Structure

```
polymarket-weather-v1/
├── alembic/           # DB migrations
│   ├── env.py
│   └── versions/
├── app/
│   ├── api/           # FastAPI routers
│   ├── core/          # config, database session
│   ├── models/        # SQLAlchemy models
│   ├── schemas/       # Pydantic schemas
│   └── main.py        # FastAPI app
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── requirements.txt
└── .env.example
```

## Tech Stack

- **FastAPI** — async web framework
- **SQLAlchemy 2** (async) + **asyncpg** — ORM + PostgreSQL driver
- **Alembic** — database migrations
- **PostgreSQL 16** — primary database
- **Docker Compose** — local orchestration
