# Architecture

## Overview

Polymarket Weather V1 is a **research and paper-trading system** that correlates Polymarket weather prediction markets with external weather probability estimates.

**No real-money execution in V1.**

## System Components

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Polymarket │────▶│   Scanner    │────▶│   PostgreSQL  │
│  Gamma API  │     │   (scan_job) │     │               │
└─────────────┘     └──────────────┘     │  source_events│
                                          │  markets      │
┌─────────────┐     ┌──────────────┐     │  market_parses│
│   Weather   │────▶│    Signal    │     │  book_snapshots│
│   Models    │     │   Scorer     │     │  signal_scores│
│   (stub)    │     └──────┬───────┘     │  paper_trades │
└─────────────┘            │             │  ...          │
                           ▼             └───────────────┘
                    ┌──────────────┐
                    │    Paper     │
                    │    Trader    │
                    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │  Evaluation  │
                    │   Engine     │
                    └──────────────┘
```

## Data Flow

1. **Scan**: Discover markets → filter binary Yes/No → identify weather markets → store
2. **Score**: Compare market prices vs weather probability → generate signals
3. **Trade**: Open paper trades based on actionable signals (1 per market)
4. **Resolve**: Check settled markets → close trades → record P&L
5. **Evaluate**: Aggregate performance stats

## Key Design Decisions (V1)

- **One open paper trade per market** — keeps things simple and auditable
- **Weather engine is a stub** — returns 0.5 probability; replace with real API later
- **Flag, don't force** — ambiguous markets are flagged, not auto-classified
- **JSONB for raw payloads** — preserves full API responses for future analysis
- **APScheduler** — periodic jobs run within the FastAPI process

## API

All routes under `/api/v1/`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| GET | /markets/recent | Recent weather markets |
| GET | /signals/recent | Recent signal scores |
| GET | /paper-trades/open | Open paper trades |
| GET | /paper-trades/resolved | Closed trades with P&L |
| GET | /evaluations/latest | Latest evaluation run |
| POST | /jobs/run-scan | Trigger market scan |
| POST | /jobs/run-resolve | Trigger resolve job |
| POST | /jobs/run-evaluate | Trigger evaluation |
