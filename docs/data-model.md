# Data Model V1.1

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
    ├──▶ (referenced by jobs)

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
**V1.1 Enhanced:** Structured data extracted from market questions.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT PK | Auto-increment |
| market_id | BIGINT FK | → markets.id |
| is_weather | BOOLEAN | Weather market detected |
| is_binary | BOOLEAN | Binary market |
| is_ambiguous | BOOLEAN | Parse confidence check |
| ambiguity_reason | TEXT | Detailed ambiguity explanation |
| location_name | VARCHAR(255) | V1.1: Extracted location |
| location_data | JSONB | V1.1: Full location data (lat, lon, etc.) |
| weather_type | VARCHAR(50) | V1.1: "temperature", "rainfall", "hurricane" |
| threshold_operator | VARCHAR(20) | V1.1: "above", "below", "at_least" |
| threshold_value | VARCHAR(100) | V1.1: Extracted threshold value |
| threshold_unit | VARCHAR(100) | V1.1: "fahrenheit", "celsius", "inches", "mm", "mph" |
| observation_window_start | VARCHAR(50) | V1.1: Observation window start |
| observation_window_end | VARCHAR(50) | V1.1: Observation window end |
| ambiguity_flags | JSONB | V1.1: List of flag strings |
| parse_meta | JSONB | Full parse details |
| parse_confidence | VARCHAR(20) | V1.1: "high", "medium", "low", "none" |
| Legacy fields | Various | metric, location, threshold, comparator (for compatibility) |

### book_snapshots
Point-in-time pricing data.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT PK | Auto-increment |
| market_id | BIGINT FK | → markets.id |
| yes_price | NUMERIC | Yes token price (0-1) |
| no_price | NUMERIC | No token price (0-1) |
| spread | NUMERIC | Bid-ask spread |
| volume_24h | NUMERIC | 24h volume |
| raw_payload | JSONB | Full API response |
| snapped_at | TIMESTAMP | Snapshot time |

### weather_model_runs
**V1.1 Enhanced:** External weather probability estimates.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT PK | Auto-increment |
| market_id | BIGINT FK | → markets.id |
| source | VARCHAR(100) | "openweathermap" |
| probability_yes | NUMERIC | Estimated P(Yes) |
| model_name | VARCHAR(100) | V1.1: Model identifier |
| forecast_date | VARCHAR(50) | V1.1: Forecast reference date |
| location | VARCHAR(255) | Location name |
| data_freshness_minutes | NUMERIC | V1.1: Age of forecast data |
| model_notes | TEXT | V1.1: Methodology and limitations |
| raw_payload | JSONB | Full weather API response |
| fetched_at | TIMESTAMP | When data was fetched |

### signal_scores
**V1.1 Enhanced:** Comparison of market price vs weather probability.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT PK | Auto-increment |
| market_id | BIGINT FK | → markets.id |
| book_snapshot_id | BIGINT FK | → book_snapshots.id |
| weather_model_id | BIGINT FK | → weather_model_runs.id |
| market_yes_price | NUMERIC | Market's Yes price |
| weather_prob | NUMERIC | Weather model's P(Yes) |
| edge | NUMERIC | weather_prob - market_price |
| direction | VARCHAR(10) | "YES" or "NO" |
| confidence | VARCHAR(20) | "high", "medium", "low" |
| recommendation | VARCHAR(50) | "buy_yes", "buy_no", "skip" |
| explainability | JSONB | V1.1: Full JSON with all fields |
| rejection_reasons | JSONB | V1.1: List of rejection reason strings |
| scored_at | TIMESTAMP | Score time |

### paper_trades
Simulated trades (no real money).

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT PK | Auto-increment |
| market_id | BIGINT FK | → markets.id |
| signal_id | BIGINT FK | → signal_scores.id |
| direction | VARCHAR(10) | "YES" or "NO" |
| entry_price | NUMERIC | Entry price |
| quantity | NUMERIC | Fixed at 1.0 in V1.1 |
| status | VARCHAR(20) | "open" or "closed" |
| exit_price | NUMERIC | Exit price (on close) |
| pnl | NUMERIC | Profit/loss |
| opened_at | TIMESTAMP | Trade open time |
| closed_at | TIMESTAMP | Trade close time |
| notes | TEXT | Trade notes |

### market_resolutions
Actual outcomes for settled markets.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT PK | Auto-increment |
| market_id | BIGINT FK | → markets.id |
| outcome | VARCHAR(10) | "Yes" or "No" |
| resolved_at | TIMESTAMP | Resolution time |
| raw_payload | JSONB | Full API response |

### evaluation_runs
Batch performance summaries.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT PK | Auto-increment |
| total_trades | INT | Total closed trades |
| winning_trades | INT | Trades with positive P&L |
| losing_trades | INT | Trades with negative P&L |
| total_pnl | NUMERIC | Sum of all P&L |
| win_rate | NUMERIC | winning / total |
| avg_edge | NUMERIC | V1.1: Average edge (replaces avg_edge) |
| details | JSONB | Breakdown by direction etc. |
| evaluated_at | TIMESTAMP | Evaluation time |

### job_runs
Execution log for all scheduled jobs.

| Column | Type | Description |
|--------|------|-------------|
| id | BIGINT PK | Auto-increment |
| job_name | VARCHAR(100) | "scan", "resolve", "evaluate" |
| status | VARCHAR(20) | "running", "success", "failed" |
| started_at | TIMESTAMP | Start time |
| finished_at | TIMESTAMP | End time |
| error | TEXT | Error message if failed |
| result_meta | JSONB | Job-specific stats |

## V1.1 Changes

### market_parses (Enhanced)
- Added V1.1 fields: `weather_type`, `location_name`, `location_data`, `threshold_operator`, `threshold_value`, `threshold_unit`, `observation_window_start`, `observation_window_end`, `ambiguity_flags`, `parse_confidence`
- Kept legacy fields for compatibility: `metric`, `location`, `threshold`, `comparator`

### weather_model_runs (Enhanced)
- Renamed from simple probability to structured result fields
- Added: `data_freshness_minutes`, `model_notes`, `forecast_date`
- Changed: `probability_yes` → V1.1 context (still stores raw probability)

### signal_scores (Enhanced)
- Added: `rejection_reasons` (JSONB list)
- Enhanced: `explainability` (JSONB) with full weather engine output
- Note: `avg_edge` field in `evaluation_runs` now holds different meaning (average of signal edges, not edge threshold)

### weather_probability_engine (NEW)
Not a table, but the V1.1 implementation in `app/engines/weather_probability.py` is a new module that replaced the stub.
