# Polymarket Weather V1.1

Research and paper-trading system for Polymarket weather prediction markets.

**No real-money execution in V1.**

## Quick Start

```bash
cd /opt/projects/polymarket-weather-v1

# 1. Copy env file
cp .env.example .env
# Edit .env and add your OpenWeatherMap API key:
# WEATHER_API_KEY=your_api_key_here

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
| GET | `/api/v1/signals/recent` | Recent signal scores |
| GET | `/api/v1/paper-trades/open` | Open paper trades |
| GET | `/api/v1/paper-trades/resolved` | Closed trades with P&L |
| GET | `/api/v1/evaluations/latest` | Latest evaluation |
| POST | `/api/v1/jobs/run-scan` | Trigger market scan |
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
│   │   ├── orderbook.py      # CLOB pricing
│   │   └── weather.py        # OpenWeatherMap client (NEW in V1.1)
│   ├── core/
│   │   ├── config.py         # Pydantic settings
│   │   └── database.py       # SQLAlchemy async session
│   ├── engines/
│   │   ├── weather_probability.py  # V1.1 real probability engine (REPLACED)
│   │   ├── signal_scorer.py        # Market vs weather scoring (ENHANCED)
│   │   └── paper_trader.py         # Paper trade management (ENHANCED)
│   ├── jobs/
│   │   ├── scan_job.py       # Market discovery
│   │   ├── resolve_job.py    # Trade settlement
│   │   └── evaluate_job.py   # Performance stats
│   ├── models/               # SQLAlchemy models (10 tables)
│   ├── parsers/
│   │   ├── binary_parser.py  # Yes/No market parser
│   │   └── weather_parser.py # Weather market identification (ENHANCED)
│   └── schemas/
├── tests/
│   ├── test_parsing.py
│   ├── test_probability.py   # Weather probability engine tests (NEW)
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

## V1.1 Weather Probability Engine

**Supported Types:**
1. **Temperature thresholds** — "Will temperature exceed X°F in [city]?"
2. **Rainfall thresholds** — "Will there be more than X inches of rain in [city]?"
3. **Hurricane/wind thresholds** — "Will wind speeds exceed X mph during hurricane in [state]?"

**Probability Estimation Methods:**

### Temperature
- Fetches 5-day/3-hour forecast from OpenWeatherMap
- Counts how many forecasted temps exceed threshold
- Uses hit ratio as base probability
- Applies Gaussian smoothing (z-score) for confidence
- Supports Fahrenheit/Celsius conversion

### Rainfall
- Uses OWM's POP (probability of precipitation) field
- Combines POP with forecasted rainfall amounts
- Adjusts probability based on actual forecasted vs threshold
- Supports inches/mm conversion

### Hurricane/Wind
- Uses forecasted wind speeds (or gusts if available)
- Counts exceedances of hurricane threshold (default 74 mph)
- **LIMITATION**: OWM provides surface winds, not hurricane-specific data
- Marks as low confidence with explicit limitation note

**Safety Rules (All Types):**
- Rejects if no location detected
- Rejects if no threshold detected
- Rejects if no observation window detected
- Reduces confidence if parser confidence is low
- Rejects if forecast data unavailable
- Halves confidence if data older than 3 hours

**V1.1 Limitations:**
- Hurricane probability uses surface wind speeds (OWM limitation)
- Does not support: tornado, flood, wildfire, drought
- No ensemble/multi-model support (uses single OWM forecast)
- Requires OpenWeatherMap API key (falls back to 0.5 with low confidence)

## Signal Scoring (V1.1)

**Enhanced rejection reasons:**
- `parser_confidence_too_low` — Parser didn't understand market well
- `stale_weather_data` — Forecast data older than 6 hours
- `unsupported_weather_type` — Weather type not in V1.1 supported list
- `ambiguous_market` — Parse flagged multiple conditions
- `edge_too_small` — Edge below 5 percentage points
- `insufficient_weather_confidence` — Weather confidence < 0.3
- `spread_too_wide` — Bid-ask spread > 10 cents
- `missing_location` — No location detected
- `insufficient_weather_data` — Forecast data unavailable

**Confidence Levels:**
- `high` — Edge ≥ 15pp AND weather confidence ≥ 0.7
- `medium` — Edge ≥ 10pp AND weather confidence ≥ 0.5
- `low` — Edge ≥ 5pp AND weather confidence ≥ 0.3

**Explainability:**
Includes all fields from weather probability engine plus rejection reasons.

## Paper Trading (V1.1)

**Enhanced safety thresholds:**
- One open trade per market (V1 rule)
- Signal must be actionable (not "skip")
- Signal confidence must be at least "low"
- Weather confidence must be ≥ 0.3
- No rejection reasons present
- Ambiguous markets rejected

**Trade Parameters:**
- Fixed quantity: 1.0 (V1)
- Entry price: market_yes_price for YES, 1.0 - market_yes_price for NO
- Exit price: 1.0 if won, 0.0 if lost
- P&L = (exit - entry) × quantity

## Key Constraints (V1.1)

- **Paper trading only** — no real money, no wallet, no private keys
- **One open trade per market** — prevents over-concentration
- **Weather engine is real** — uses OpenWeatherMap API
- **Ambiguous markets flagged** — not auto-traded
- **Binary Yes/No only** — multi-outcome markets are skipped
- **Limited weather types** — only temperature, rainfall, hurricane/wind in V1.1
