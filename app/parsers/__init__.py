"""Binary yes/no market parser."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def is_binary_market(market: dict[str, Any]) -> bool:
    """Check if a market is a simple binary Yes/No market."""
    outcomes_raw = market.get("outcomes", "[]")
    if isinstance(outcomes_raw, str):
        try:
            outcomes = json.loads(outcomes_raw)
        except json.JSONDecodeError:
            return False
    elif isinstance(outcomes_raw, list):
        outcomes = outcomes_raw
    else:
        return False

    if len(outcomes) != 2:
        return False
    return set(o.lower() for o in outcomes) == {"yes", "no"}


def parse_binary_market(market: dict[str, Any]) -> dict[str, Any]:
    """Parse a binary market and extract key fields."""
    prices_raw = market.get("outcomePrices", "[]")
    if isinstance(prices_raw, str):
        try:
            prices = json.loads(prices_raw)
        except json.JSONDecodeError:
            prices = [None, None]
    else:
        prices = prices_raw

    yes_price = float(prices[0]) if prices and prices[0] is not None else None
    no_price = float(prices[1]) if len(prices) > 1 and prices[1] is not None else None

    return {
        "polymarket_id": market.get("id", ""),
        "question": market.get("question", ""),
        "slug": market.get("slug", ""),
        "description": market.get("description", ""),
        "end_date": market.get("endDate", ""),
        "yes_price": yes_price,
        "no_price": no_price,
        "volume": float(market.get("volumeNum", 0) or 0),
        "liquidity": float(market.get("liquidityNum", 0) or 0),
        "active": market.get("active", False),
        "closed": market.get("closed", False),
        "is_binary": True,
        "raw": market,
    }
