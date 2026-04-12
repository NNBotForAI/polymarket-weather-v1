"""Resolve job — check resolved markets and settle paper trades."""

import logging
from datetime import datetime, timezone

from sqlalchemy import select, and_

from app.clients import search_markets
from app.core.database import async_session
from app.engines.paper_trader import settle_trade
from app.models.job_runs import JobRun
from app.models.market_resolutions import MarketResolution
from app.models.markets import Market
from app.models.paper_trades import PaperTrade

logger = logging.getLogger(__name__)


async def run_resolve() -> dict:
    """Check for resolved markets and settle open paper trades."""
    job = JobRun(
        job_name="resolve",
        status="running",
        started_at=datetime.now(timezone.utc),
    )

    stats = {"checked": 0, "resolved": 0, "trades_settled": 0}

    async with async_session() as session:
        session.add(job)
        await session.flush()

        try:
            # Find open trades with their markets
            result = await session.execute(
                select(PaperTrade, Market)
                .join(Market, PaperTrade.market_id == Market.id)
                .where(PaperTrade.status == "open")
            )
            open_trades = result.all()

            stats["checked"] = len(open_trades)

            for trade, market in open_trades:
                # Check if market is now closed
                try:
                    results = await search_markets(query=None, limit=1, closed=True)
                    # Try to find this specific market
                    pm_data = None
                    for m in results:
                        if str(m.get("id")) == market.polymarket_id:
                            pm_data = m
                            break

                    if not pm_data or not pm_data.get("closed"):
                        continue

                except Exception as e:
                    logger.warning("Failed to check market %s: %s", market.polymarket_id, e)
                    continue

                # Determine resolution
                import json
                prices_raw = pm_data.get("outcomePrices", "[]")
                if isinstance(prices_raw, str):
                    prices = json.loads(prices_raw)
                else:
                    prices = prices_raw

                yes_price = float(prices[0]) if prices and prices[0] else None
                if yes_price is None:
                    continue

                outcome = "Yes" if yes_price > 0.5 else "No"

                # Record resolution
                resolution = MarketResolution(
                    market_id=market.id,
                    outcome=outcome,
                    resolved_at=datetime.now(timezone.utc),
                    raw_payload=pm_data,
                )
                session.add(resolution)

                # Settle trade
                settlement = settle_trade(
                    {
                        "direction": trade.direction,
                        "entry_price": float(trade.entry_price),
                        "quantity": float(trade.quantity),
                        "notes": trade.notes,
                    },
                    outcome,
                )
                trade.exit_price = settlement["exit_price"]
                trade.pnl = settlement["pnl"]
                trade.status = settlement["status"]
                trade.closed_at = settlement["closed_at"]
                trade.notes = settlement["notes"]

                # Mark market as closed
                market.closed = True

                stats["resolved"] += 1
                stats["trades_settled"] += 1

            job.status = "success"
            job.result_meta = stats

        except Exception as e:
            logger.exception("Resolve job failed")
            job.status = "failed"
            job.error = str(e)

        job.finished_at = datetime.now(timezone.utc)
        await session.commit()

    logger.info("Resolve complete: %s", stats)
    return stats
