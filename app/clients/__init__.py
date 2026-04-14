"""Gamma API client — Polymarket market discovery."""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GAMMA_BASE = settings.polymarket_api_base


async def search_markets(
    query: str | None = None,
    tag: str | None = None,
    closed: bool = False,
    limit: int = 100,
    offset: int = 0,
    order: str = "end_date_iso",
    ascending: bool = True,
) -> list[dict[str, Any]]:
    """Search Polymarket markets via the Gamma API /markets endpoint."""
    params: dict[str, Any] = {
        "closed": str(closed).lower(),
        "limit": limit,
        "offset": offset,
        "order": order,
        "ascending": str(ascending).lower(),
    }
    if query:
        params["tag"] = query
    if tag:
        params["tag"] = tag

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{GAMMA_BASE}/markets", params=params)
        resp.raise_for_status()
        return resp.json()


async def public_search(query: str, limit: int = 50) -> dict[str, Any]:
    """Search events, markets and profiles via /public-search.

    Returns dict with 'events' key containing matching events.
    Each event has a 'markets' list with individual market data.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{GAMMA_BASE}/public-search",
            params={"q": query, "limit": limit},
        )
        resp.raise_for_status()
        return resp.json()


async def get_market(condition_id: str) -> dict[str, Any] | None:
    """Fetch a single market by condition_id."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{GAMMA_BASE}/markets", params={"conditionId": condition_id})
        resp.raise_for_status()
        data = resp.json()
        return data[0] if data else None


async def get_events(
    tag: str | None = None,
    closed: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    """Fetch events (groups of markets)."""
    params: dict[str, Any] = {
        "closed": str(closed).lower(),
        "limit": limit,
        "offset": offset,
    }
    if tag:
        params["tag"] = tag

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{GAMMA_BASE}/events", params=params)
        resp.raise_for_status()
        return resp.json()
