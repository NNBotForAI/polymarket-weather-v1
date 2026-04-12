"""Scan job — discover new weather markets from Polymarket."""

import hashlib
import json
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.clients import search_markets
from app.core.database import async_session
from app.models.book_snapshots import BookSnapshot
from app.models.job_runs import JobRun
from app.models.markets import Market
from app.models.market_parses import MarketParse
from app.models.source_events import SourceEvent
from app.parsers.binary_parser import is_binary_market, parse_binary_market
from app.parsers.weather_parser import is_weather_market, parse_weather_market

logger = logging.getLogger(__name__)


async def run_scan() -> dict:
    """Scan Polymarket for new weather-related binary markets.

    Returns summary dict with counts.
    """
    job = JobRun(
        job_name="scan",
        status="running",
        started_at=datetime.now(timezone.utc),
    )

    stats = {"discovered": 0, "new_markets": 0, "weather_markets": 0, "skipped": 0}

    async with async_session() as session:
        session.add(job)
        await session.flush()

        try:
            # Search for weather-related markets
            keywords = [
                "weather", "temperature", "rain", "snow", "hurricane",
                "tornado", "flood", "storm", "heat", "cold",
            ]

            all_raw: list[dict] = []
            for kw in keywords:
                try:
                    results = await search_markets(query=kw, limit=50, closed=False)
                    all_raw.extend(results)
                except Exception as e:
                    logger.warning("Search failed for keyword '%s': %s", kw, e)

            # Deduplicate by polymarket_id
            seen_ids: set[str] = set()
            unique_markets: list[dict] = []
            for m in all_raw:
                pm_id = str(m.get("id", ""))
                if pm_id and pm_id not in seen_ids:
                    seen_ids.add(pm_id)
                    unique_markets.append(m)

            stats["discovered"] = len(unique_markets)

            for raw in unique_markets:
                if not is_binary_market(raw):
                    stats["skipped"] += 1
                    continue

                pm_id = str(raw["id"])

                # Check if we already have this market
                existing = await session.execute(
                    select(Market).where(Market.polymarket_id == pm_id)
                )
                if existing.scalar_one_or_none():
                    continue

                # Store source event
                payload_str = json.dumps(raw, sort_keys=True, default=str)
                sha256 = hashlib.sha256(payload_str.encode()).hexdigest()

                source_event = SourceEvent(
                    source="polymarket_gamma",
                    event_type="market_discovery",
                    raw_payload=raw,
                    sha256=sha256,
                )
                session.add(source_event)

                # Parse market
                parsed = parse_binary_market(raw)
                weather_info = parse_weather_market(parsed["question"])

                market = Market(
                    polymarket_id=pm_id,
                    question=parsed["question"],
                    slug=parsed["slug"],
                    description=parsed["description"],
                    outcomes={"yes": parsed["yes_price"], "no": parsed["no_price"]},
                    is_binary=True,
                    is_weather=weather_info["is_weather"],
                    end_date=parsed["end_date"] or None,
                    active=parsed["active"],
                    closed=parsed["closed"],
                    volume=parsed["volume"],
                    liquidity=parsed["liquidity"],
                    raw_payload=raw,
                )
                session.add(market)
                await session.flush()

                # Store parse
                market_parse = MarketParse(
                    market_id=market.id,
                    is_weather=weather_info["is_weather"],
                    is_binary=True,
                    is_ambiguous=weather_info["is_ambiguous"],
                    ambiguity_reason=weather_info.get("ambiguity_reason"),
                    location=weather_info.get("location"),
                    metric=weather_info.get("metric"),
                    threshold=weather_info.get("threshold"),
                    comparator=weather_info.get("comparator"),
                    target_date=weather_info.get("target_date"),
                    parse_meta=weather_info,
                )
                session.add(market_parse)

                # Store initial book snapshot
                snapshot = BookSnapshot(
                    market_id=market.id,
                    yes_price=parsed["yes_price"],
                    no_price=parsed["no_price"],
                    raw_payload=raw,
                    snapped_at=datetime.now(timezone.utc),
                )
                session.add(snapshot)

                stats["new_markets"] += 1
                if weather_info["is_weather"]:
                    stats["weather_markets"] += 1

            job.status = "success"
            job.result_meta = stats

        except Exception as e:
            logger.exception("Scan job failed")
            job.status = "failed"
            job.error = str(e)

        job.finished_at = datetime.now(timezone.utc)
        await session.commit()

    logger.info("Scan complete: %s", stats)
    return stats
