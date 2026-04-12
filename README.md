# Polymarket Weather V1

Research and paper-trading system for Polymarket weather prediction markets.

**No real-money execution in V1.**

## Quick Start

```bash
cd /opt/projects/polymarket-weather-v1

# 1. Copy env file
cp .env.example .env

# 2. Start services (app + postgres)
docker compose up -d --build

# 3. Run database migrations
docker compose exec app alembic upgrade head

# 4. Verify
curl http://localhost:8000/health
# → {"status":"ok","service":"polymarket-weather-v1"}
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/markets/recent` | Recent weather markets |
| GET | `/api/v1/signals/recent` | Signal scores |
| GET | `/api/v1/paper-trades/open` | Open trades |
| GET | `/api/v1/paper-trades/resolved` | Closed trades |
| GET | `/api/v1/evaluations/latest` | Latest evaluation |
| POST | `/api/v1/jobs/run-scan` | Trigger scan |
| POST | `/api/v1/jobs/run-resolve` | Trigger resolve |
| POST | `/api/v1/jobs/run-evaluate` | Trigger evaluation |

## Project Structure

```
polymarket-weather-v1/
├── alembic/                  # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── alembic.ini
├── app/
│   ├── main.py               # FastAPI app + scheduler
│   ├── api/
│   │   ├── health.py         # GET /health
│   │   └── routes.py         # All API routes
│   ├── clients/
│   │   ├── gamma.py          # Polymarket market discovery
│   │   └── orderbook.py      # CLOB pricing
│   ├── core/
│   │   ├── config.py         # Pydantic settings
│   │   └── database.py       # SQLAlchemy async session
│   ├── engines/
│   │   ├── weather_probability.py  # Weather prob (stub)
│   │   ├── signal_scorer.py        # Market vs weather scoring
│   │   └── paper_trader.py         # Paper trade management
│   ├── jobs/
│   │   ├── scan_job.py       # Market discovery
│   │   ├── resolve_job.py    # Trade settlement
│   │   └── evaluate_job.py   # Performance stats
│   ├── models/               # SQLAlchemy models (10 tables)
│   ├── parsers/
│   │   ├── binary_parser.py  # Yes/No market parser
│   │   └── weather_parser.py # Weather market identification
│   └── schemas/
├── tests/
│   ├── test_parsing.py
│   ├── test_scoring.py
│   └── test_settlement.py
├── docs/
│   ├── architecture.md
│   ├── data-model.md
│   └── jobs.md
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── requirements.txt
```

## Development

```bash
# Run tests locally
pip install -r requirements.txt
python -m pytest tests/ -v

# Create a new migration
docker compose exec app alembic revision --autogenerate -m "description"

# View logs
docker compose logs -f app
```

## Key Constraints (V1)

- **Paper trading only** — no real money, no wallet, no private keys
- **One open trade per market** — prevents over-concentration
- **Weather engine is stub** — returns 0.5 probability; needs real API integration
- **Ambiguous markets flagged** — not auto-traded
- **Binary Yes/No only** — multi-outcome markets are skipped
