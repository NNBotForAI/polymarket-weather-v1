# Data Model

## Entity Relationship

```
source_events ──┐
                │
markets ────────┤──▶ market_parses
    │           │
    ├──▶ book_snapshots
    │
    ├──▶ weather_model_runs
    │
    ├──▶ signal_scores ──▶ paper_trades
    │                           │
    ├──▶ market_resolutions ────┘ (settlement)
    │
    └──▶ (referenced by jobs)

evaluation_runs  (aggregated stats)
job_runs         (execution logs)
```

## Tables

### source_events
Raw payloads from Polymarket API. Deduplicated by SHA-256 hash.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT PK | Auto-increment |
| source | VARCHAR(50) | "polymarket_gamma" |
| event_type | VARCHAR(100) | "market_discovery" |
| raw_payload | JSONB | Full API response |
| sha256 | VARCHAR(64) | Dedup hash |

### markets
Normalized market records.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT PK | Auto-increment |
| polymarket_id | VARCHAR(100) | Polymarket market ID (unique) |
| question | TEXT | Market question |
| slug | VARCHAR(255) | URL slug |
| is_binary | BOOLEAN | Is Yes/No binary market |
| is_weather | BOOLEAN | Is weather-related |
| end_date | TIMESTAMP | Market expiry |
| active | BOOLEAN | Currently active |
| closed | BOOLEAN | Resolved/closed |
| volume | NUMERIC | Trading volume |
| liquidity | NUMERIC | Available liquidity |
| raw_payload | JSONB | Full API response |

### market_parses
Structured data extracted from market questions.

| Column | Type | Description |
|--------|------|-------------|
| market_id | BIGINT FK | → markets.id |
| is_weather | BOOLEAN | Weather market detected |
| is_binary | BOOLEAN | Binary market |
| is_ambiguous | BOOLEAN | Parse confidence |
| location | VARCHAR(255) | Geographic location |
| metric | VARCHAR(100) | "temperature", "rainfall", etc. |
| threshold | VARCHAR(100) | Threshold value |
| comparator | VARCHAR(20) | "above", "below", etc. |
| target_date | VARCHAR(50) | Date reference |
| parse_meta | JSONB | Full parse details |

### book_snapshots
Point-in-time pricing data.

| Column | Type | Description |
|--------|------|-------------|
| market_id | BIGINT FK | → markets.id |
| yes_price | NUMERIC | Yes token price (0-1) |
| no_price | NUMERIC | No token price (0-1) |
| spread | NUMERIC | Bid-ask spread |
| snapped_at | TIMESTAMP | Snapshot time |

### weather_model_runs
External weather probability estimates.

| Column | Type | Description |
|--------|------|-------------|
| market_id | BIGINT FK | → markets.id |
| source | VARCHAR(100) | "openweathermap", "noaa" |
| probability_yes | NUMERIC | Estimated P(Yes) |
| model_name | VARCHAR(100) | Model identifier |
| fetched_at | TIMESTAMP | When data was fetched |

### signal_scores
Comparison of market price vs weather probability.

| Column | Type | Description |
|--------|------|-------------|
| market_id | BIGINT FK | → markets.id |
| market_yes_price | NUMERIC | Market's Yes price |
| weather_prob | NUMERIC | Weather model's P(Yes) |
| edge | NUMERIC | weather_prob - market_price |
| direction | VARCHAR(10) | "YES" or "NO" |
| confidence | VARCHAR(20) | "high", "medium", "low" |
| recommendation | VARCHAR(50) | "buy_yes", "buy_no", "skip" |
| explainability | JSONB | Full reasoning |

### paper_trades
Simulated trades (no real money).

| Column | Type | Description |
|--------|------|-------------|
| market_id | BIGINT FK | → markets.id |
| signal_id | BIGINT FK | → signal_scores.id |
| direction | VARCHAR(10) | "YES" or "NO" |
| entry_price | NUMERIC | Entry price |
| quantity | NUMERIC | Fixed at 1.0 in V1 |
| status | VARCHAR(20) | "open" or "closed" |
| exit_price | NUMERIC | Exit price (on close) |
| pnl | NUMERIC | Profit/loss |
| opened_at | TIMESTAMP | Trade open time |
| closed_at | TIMESTAMP | Trade close time |

### market_resolutions
Actual outcomes for settled markets.

| Column | Type | Description |
|--------|------|-------------|
| market_id | BIGINT FK | → markets.id |
| outcome | VARCHAR(10) | "Yes" or "No" |
| resolved_at | TIMESTAMP | Resolution time |

### evaluation_runs
Batch performance summaries.

| Column | Type | Description |
|--------|------|-------------|
| total_trades | INT | Total closed trades |
| winning_trades | INT | Trades with positive P&L |
| total_pnl | NUMERIC | Sum of all P&L |
| win_rate | NUMERIC | winning / total |
| details | JSONB | Breakdown by direction etc. |

### job_runs
Execution log for all scheduled jobs.

| Column | Type | Description |
|--------|------|-------------|
| job_name | VARCHAR(100) | "scan", "resolve", "evaluate" |
| status | VARCHAR(20) | "running", "success", "failed" |
| started_at | TIMESTAMP | Start time |
| finished_at | TIMESTAMP | End time |
| error | TEXT | Error message if failed |
| result_meta | JSONB | Job-specific stats |
