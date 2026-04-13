# Jobs V1.1

## Scheduled Jobs

Three jobs run on automatic schedules via APScheduler:

| Job | Schedule | Description |
|-----|----------|-------------|
| **scan** | Every 6 hours | Discover new weather markets + fetch weather data |
| **resolve** | Every 12 hours | Check resolved markets, settle paper trades |
| **evaluate** | Every 24 hours | Compute P&L and accuracy stats |

All jobs can also be triggered manually via API.

## Scan Job

**Purpose:** Find new weather-related binary markets on Polymarket and generate weather probability estimates.

**V1.1 Changes:**
- Now calls OpenWeatherMap to fetch forecast data
- Generates real probability estimates using type-specific estimators
- Stores weather_model_runs records with confidence scores

**Flow:**
1. Search Polymarket Gamma API with weather keywords
2. Deduplicate results by market ID
3. Filter for binary Yes/No markets only
4. Skip already-known markets
5. Store raw API response as `source_event`
6. Create normalized `market` record
7. **NEW:** Run enhanced weather parser to extract V1.1 structured data
8. Store `market_parse` with V1.1 fields (weather_type, location_name, etc.)
9. **NEW:** Call OpenWeatherMap to fetch forecast data
10. **NEW:** Call weather probability engine to estimate P(event)
11. Store `weather_model_run` with probability and confidence
12. Store initial `book_snapshot`

**API Trigger:** `POST /api/v1/jobs/run-scan`

## Resolve Job

**Purpose:** Check if markets have resolved and settle open paper trades.

**Flow:**
1. Find all paper trades with status "open"
2. For each, check if the underlying market is now closed
3. Determine outcome (Yes/No) from final prices
4. Create `market_resolution` record
5. Calculate P&L for trade
6. Update paper trade with exit_price, pnl, status="closed"
7. Mark market as closed

**API Trigger:** `POST /api/v1/jobs/run-resolve`

## Evaluate Job

**Purpose:** Aggregate performance statistics across all closed paper trades.

**Flow:**
1. Query all closed paper trades
2. Compute: total trades, wins, losses, total P&L, win rate
3. **V1.1:** Compute average signal edge (different from V1.0 avg_edge)
4. Break down by direction (YES vs NO)
5. Store as `evaluation_run`

**API Trigger:** `POST /api/v1/jobs/run-evaluate`

## Job Run Logging

Every job execution creates a `job_run` record with:
- Start/end timestamps
- Status (running → success/failed)
- Error details if failed
- Result metadata (counts, stats)

## V1.1 Weather Probability Pipeline

The scan job now includes a full weather probability pipeline:

```
Market Question
       │
       ▼
Enhanced Weather Parser
       │
       ├── weather_type (temperature/rainfall/hurricane)
       ├── location_name + location_data (lat/lon)
       ├── threshold_value + threshold_unit + threshold_operator
       ├── observation_window (start/end)
       └── parse_confidence
       │
       ▼
OpenWeatherMap Client
       │
       ▼
Forecast Data
       │
       ▼
Weather Probability Engine
       │
       ├── Temperature Estimator (hit ratio + z-score)
       ├── Rainfall Estimator (POP + amount ratio)
       └── Hurricane Estimator (wind exceedance)
       │
       ▼
ProbabilityResult
       ├── true_prob_raw
       ├── confidence_score (0.0–1.0)
       ├── data_freshness_minutes
       ├── model_notes (methodology)
       └── feature_json (all parameters)
```

## Rejection Reasons (V1.1)

The scan job now has enhanced rejection checking before creating trades:

| Rejection | When Occurs |
|-----------|-------------|
| `parser_confidence_too_low` | Weather parser confidence = "low" |
| `stale_weather_data` | Forecast data older than 6 hours |
| `unsupported_weather_type` | Weather type not in {temperature, rainfall, hurricane} |
| `ambiguous_market` | Parse flagged multiple conditions |
| `edge_too_small` | Edge below 5 percentage points |
| `insufficient_weather_confidence` | Weather confidence < 0.3 |
| `spread_too_wide` | Bid-ask spread > 10 cents |
| `missing_location` | No location detected |
| `insufficient_weather_data` | Forecast data unavailable |

Each rejected signal has its `rejection_reasons` list populated with these structured reasons, making it clear why a trade was not opened.
