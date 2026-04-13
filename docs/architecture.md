# Architecture V1.1

## Overview

Polymarket Weather V1.1 is a **research and paper-trading system** that correlates Polymarket weather prediction markets with **real weather probability estimates** from OpenWeatherMap.

**No real-money execution.**

## System Components

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Polymarket │────▶│   Scanner    │────▶│   PostgreSQL  │
│  Gamma API  │     │   (scan_job) │     │               │
└─────────────┘     └──────────────┘     │  source_events│
                                          │  markets      │
┌─────────────┐     ┌──────────────┐     │  market_parses│
│  OpenWeather │────▶│  Weather     │────▶│  book_snapshots│
│    Map API  │     │  Probability│     │               │
└─────────────┘     └───────────────┘     │  signal_scores│
                    │             │         │               │
                    └──────────────┘         │  paper_trades │
                           │             │         │               │
                           ▼             └─────────┘     └───────────────┘
                    ┌──────────────┐     ┌──────────────┐
                    │   Signal     │────▶│    Paper     │
                    │   Scorer     │     │    Trader     │
                    └──────────────┘     └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Evaluation  │
                    │   Engine     │
                    └──────────────┘
```

## Data Flow

1. **Scan**: Discover markets → filter binary Yes/No → identify weather markets → store
2. **Parse**: Extract structured data (location, type, threshold, unit, window)
3. **Fetch Weather**: Call OpenWeatherMap for forecast data
4. **Probability**: Estimate P(event is true) using forecast statistics
5. **Score**: Compare market prices vs weather probability → generate signals
6. **Trade**: Open paper trades based on actionable signals (1 per market)
7. **Resolve**: Check settled markets → close trades → record P&L
8. **Evaluate**: Aggregate performance stats

## Key Design Decisions (V1.1)

- **One open paper trade per market** — keeps things simple and auditable
- **Real weather probability engine** — uses OpenWeatherMap with statistical methods
- **Support for 3 weather types only** — temperature, rainfall, hurricane/wind
- **Flag, don't force** — ambiguous markets are flagged, not auto-classied
- **JSONB for raw payloads** — preserves full API responses
- **Structured rejection reasons** — clear explanation why signal was rejected
- **Freshness tracking** — older forecast data gets lower confidence
- **APScheduler** — periodic jobs run within FastAPI process

## Weather Probability Engine (V1.1)

The core innovation in V1.1 is the replacement of the stub with a real probability engine.

### Architecture

```
Market Question
       │
       ▼
Weather Parser
       │
       ▼
Structured Data (type, location, threshold, unit, window)
       │
       ▼
OpenWeatherMap Client
       │
       ▼
Forecast Data (current + 5-day/3-hour)
       │
       ▼
Weather Probability Engine
       │
       ├─ Temperature Estimator
       ├─ Rainfall Estimator
       └─ Hurricane Estimator
       │
       ▼
ProbabilityResult (prob, confidence, freshness, features)
       │
       ▼
Signal Scorer
```

### Type-Specific Estimation

#### Temperature
- Method: Forecast hit ratio with Gaussian smoothing
- Count forecasted temps meeting threshold
- Z-score based confidence calculation
- Support for °F/°C conversion
- Confidence: 0.4–0.95 based on forecast spread and proximity to threshold

#### Rainfall
- Method: POP + amount ratio
- Use OWM's probability of precipitation as base
- Adjust based on forecasted rainfall amount vs threshold
- Support for inches/mm conversion
- Confidence: 0.3–0.85 based on forecast data density

#### Hurricane/Wind
- Method: Wind speed exceedance count
- Count forecasted wind speeds exceeding hurricane threshold (default 74 mph)
- **Limitation**: Uses surface winds (OWM limitation), not hurricane-specific
- Confidence: Hard-capped at 0.4 due to data limitation
- Note: Real hurricane probability requires NHC (National Hurricane Center) data

### Safety Mechanisms

1. **Pre-flight checks**:
   - Not a weather market → reject
   - Weather type not supported → reject
   - Missing location → reject
   - Missing threshold → reject
   - Missing observation window → reject
   - Parser confidence too low → reject

2. **Freshness penalty**:
   - Forecast data older than 3 hours → confidence × 0.5
   - Tracks data age in minutes

3. **Parser confidence multiplier**:
   - Low parse confidence → confidence × 0.8
   - Reduces signal confidence when market question is ambiguous

## Signal Scoring (V1.1)

Enhanced with structured rejection reasons and explainability.

**Score components:**
1. `edge` — weather_prob - market_price
2. `direction` — "YES", "NO", or None
3. `confidence` — "high", "medium", "low", or "none"
4. `recommendation` — "buy_yes", "buy_no", or "skip"
5. `rejection_reasons` — structured list of why signal was rejected
6. `explainability` — full JSON with all components

**Rejection reasons:**
| Reason | Description |
|--------|-------------|
| `parser_confidence_too_low` | Market question parsing had low confidence |
| `stale_weather_data` | Forecast data older than 6 hours |
| `unsupported_weather_type` | Weather type not in supported list |
| `ambiguous_market` | Parse flagged multiple conditions |
| `edge_too_small` | Edge below 5pp |
| `insufficient_weather_confidence` | Weather confidence < 0.3 |
| `spread_too_wide` | Bid-ask spread > 10 cents |
| `missing_location` | No location detected |
| `insufficient_weather_data` | Forecast data unavailable |

## Paper Trading (V1.1)

**Safety thresholds:**
- Signal must have direction (YES/NO)
- Signal confidence must be at least "low"
- Weather confidence must be ≥ 0.3
- No rejection reasons present
- One trade per market rule
- Ambiguous markets rejected

**Trade parameters:**
- Fixed quantity: 1.0
- Entry: YES → market_yes_price; NO → 1.0 - market_yes_price
- Exit: 1.0 (won) or 0.0 (lost)
- P&L: (exit - entry) × 1.0

## API

All routes under `/api/v1/`:

| Endpoint | Description |
|----------|-------------|
| /health | Health check |
| /markets/recent | Recent weather markets |
| /signals/recent | Recent signal scores with rejection reasons |
| /paper-trades/open | Open paper trades |
| /paper-trades/resolved | Closed trades with P&L |
| /evaluations/latest | Latest evaluation run |
| /jobs/run-scan | Trigger market scan |
| /jobs/run-resolve | Trigger resolve job |
| /jobs/run-evaluate | Trigger evaluation |

## Scheduled Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| **scan** | Every 6 hours | Discover new weather markets |
| **resolve** | Every 12 hours | Check resolved markets, settle trades |
| **evaluate** | Every 24 hours | Compute P&L and accuracy stats |
