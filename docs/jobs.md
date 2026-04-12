# Jobs

## Scheduled Jobs

Three jobs run on automatic schedules via APScheduler:

| Job | Schedule | Description |
|-----|----------|-------------|
| **scan** | Every 6 hours | Discover new weather markets |
| **resolve** | Every 12 hours | Check resolved markets, settle trades |
| **evaluate** | Every 24 hours | Compute P&L and accuracy stats |

All jobs can also be triggered manually via the API.

## Scan Job

**Purpose**: Find new weather-related binary markets on Polymarket.

**Flow**:
1. Search Polymarket Gamma API with weather keywords
2. Deduplicate results by market ID
3. Filter for binary Yes/No markets only
4. Skip already-known markets
5. Store raw API response as `source_event`
6. Create normalized `market` record
7. Run weather parser to extract location/metric/threshold
8. Store `market_parse` with structured data
9. Store initial `book_snapshot`

**API Trigger**: `POST /api/v1/jobs/run-scan`

## Resolve Job

**Purpose**: Check if markets have resolved and settle open paper trades.

**Flow**:
1. Find all paper trades with status "open"
2. For each, check if the underlying market is now closed
3. Determine outcome (Yes/No) from final prices
4. Create `market_resolution` record
5. Calculate P&L for the trade
6. Update paper trade with exit_price, pnl, status="closed"
7. Mark market as closed

**API Trigger**: `POST /api/v1/jobs/run-resolve`

## Evaluate Job

**Purpose**: Aggregate performance statistics across all closed trades.

**Flow**:
1. Query all closed paper trades
2. Compute: total trades, wins, losses, total P&L, win rate
3. Break down by direction (YES vs NO)
4. Store as `evaluation_run`

**API Trigger**: `POST /api/v1/jobs/run-evaluate`

## Job Run Logging

Every job execution creates a `job_run` record with:
- Start/end timestamps
- Status (running → success/failed)
- Error details if failed
- Result metadata (counts, stats)
