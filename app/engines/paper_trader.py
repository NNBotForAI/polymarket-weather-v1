"""Paper trading engine — manage simulated trades (no real money)."""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


def should_open_trade(
    signal: dict[str, Any],
    existing_open_trades: list[dict[str, Any]],
) -> tuple[bool, str]:
    """Determine if we should open a paper trade.

    V1 rule: one open trade per market.

    Returns (should_open, reason).
    """
    market_id = signal["market_id"]

    # Check for existing open trade on same market
    for trade in existing_open_trades:
        if trade["market_id"] == market_id and trade["status"] == "open":
            return False, f"Already have open trade #{trade['id']} for market {market_id}"

    # Only trade on actionable signals
    if signal["recommendation"] == "skip":
        return False, "Signal recommendation is 'skip'"

    if signal["direction"] not in ("YES", "NO"):
        return False, f"Invalid direction: {signal['direction']}"

    return True, "Signal actionable, no existing open trade"


def create_trade_params(signal: dict[str, Any]) -> dict[str, Any]:
    """Build paper trade parameters from a signal."""
    direction = signal["direction"]
    if direction == "YES":
        entry_price = signal["market_yes_price"]
    else:
        entry_price = 1.0 - signal["market_yes_price"]

    return {
        "market_id": signal["market_id"],
        "signal_id": signal.get("id", 0),
        "direction": direction,
        "entry_price": entry_price,
        "quantity": 1.0,  # V1: fixed size
        "status": "open",
        "opened_at": datetime.now(timezone.utc),
        "notes": f"Signal edge: {signal.get('edge', 0):.2%}, confidence: {signal.get('confidence', 'unknown')}",
    }


def settle_trade(trade: dict[str, Any], resolution_outcome: str) -> dict[str, Any]:
    """Settle a paper trade given the market resolution.

    Args:
        trade: Paper trade dict
        resolution_outcome: "Yes" or "No"

    Returns:
        Updated trade fields (exit_price, pnl, status, closed_at).
    """
    direction = trade["direction"]
    entry_price = float(trade["entry_price"])
    quantity = float(trade["quantity"])

    won = (direction == "YES" and resolution_outcome == "Yes") or \
          (direction == "NO" and resolution_outcome == "No")

    if won:
        exit_price = 1.0
        pnl = (exit_price - entry_price) * quantity
    else:
        exit_price = 0.0
        pnl = (exit_price - entry_price) * quantity

    return {
        "exit_price": exit_price,
        "pnl": round(pnl, 6),
        "status": "closed",
        "closed_at": datetime.now(timezone.utc),
        "notes": (trade.get("notes") or "") + f" | Settled: resolution={resolution_outcome}, pnl={pnl:+.4f}",
    }
