"""Public order book pricing client for Polymarket CLOB."""

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

CLOB_BASE = "https://clob.polymarket.com"


async def get_market_prices(token_id: str) -> dict[str, Any] | None:
    """Get current yes/no prices from the CLOB order book."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(f"{CLOB_BASE}/prices", params={"token_id": token_id})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.warning("Failed to fetch prices for token %s: %s", token_id, e)
            return None


async def get_order_book(token_id: str) -> dict[str, Any] | None:
    """Get full order book for a token."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(f"{CLOB_BASE}/book", params={"token_id": token_id})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            logger.warning("Failed to fetch order book for token %s: %s", token_id, e)
            return None
