# Polymarket Weather v1

Correlation engine between Polymarket prediction markets and weather data.

## Quick Start

```bash
# 1. Clone & enter project
cd /opt/projects/polymarket-weather-v1

# 2. Copy env file and edit
cp .env.example .env
# edit .env with your keys

# 3. Start services
docker compose up -d --build

# 4. Check health
curl http://localhost:8000/health

# 5. Run migrations
docker compose exec app alembic upgrade head
```

## Project Structure

```
polymarket-weather-v1/
├── alembic/                 # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── alembic.ini
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── api/
│   │   ├── __init__.py
│   │   └── health.py        # GET /health
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py         # Pydantic settings
│   │   └── database.py       # SQLAlchemy async session
│   ├── models/
│   │   ├── __init__.py
│   │   └── base.py           # DeclarativeBase + TimestampMixin
│   └── schemas/
│       └── __init__.py
├── docker-compose.yml
├── Dockerfile
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## Development

```bash
# Local dev with auto-reload
docker compose up -d --build
docker compose logs -f app

# Create a migration
docker compose exec app alembic revision --autogenerate -m "description"

# Apply migrations
docker compose exec app alembic upgrade head
```

## API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Service health check |
