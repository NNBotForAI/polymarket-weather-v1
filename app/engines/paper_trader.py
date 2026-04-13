"""Paper trading engine V1.1 — manage simulated trades with safety thresholds.

Enhanced with: confidence, ambiguity, and rejection checks.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Minimum confidence to allow paper trade
MIN_SIGNAL_CONFIDENCE = "low"  # "high", "medium", "low" → allow low+
CONFIDENCE_ORDER = {"none": 0, "low": 1, "medium": 2, "high": 3}

# Minimum weather confidence score
MIN_WEATHER_CONFIDENCE = 0.3


def should_open_trade(
    signal: dict[str, Any],
    existing_open_trades: list[dict[str, Any]],
) -> tuple[bool, str]:
    """Determine if we should open a paper trade.

    Checks:
    - One open trade per market (V1 rule)
    - Signal must be actionable (not skip)
    - Signal confidence must be sufficient
    - No rejection reasons
    - Weather confidence must be sufficient
    - Ambiguous markets rejected

    Returns (should_open, reason).
    """
    market_id = signal["market_id"]

    # 1. Check for existing open trade on same market
    for trade in existing_open_trades:
        if trade["market_id"] == market_id and trade["status"] == "open":
            return False, f"already_have_open_trade:{trade['id']}"

    # 2. Must be actionable
    recommendation = signal.get("recommendation", "skip")
    if recommendation == "skip":
        reasons = signal.get("rejection_reasons", [])
        return False, f"signal_skip:{','.join(reasons) if reasons else 'no_reason'}"

    # 3. Direction must be valid
    direction = signal.get("direction")
    if direction not in ("YES", "NO"):
        return False, f"invalid_direction:{direction}"

    # 4. Signal confidence check
    confidence = signal.get("confidence", "none")
    if CONFIDENCE_ORDER.get(confidence, 0) < CONFIDENCE_ORDER.get(MIN_SIGNAL_CONFIDENCE, 1):
        return False, f"signal_confidence_too_low:{confidence}"

    # 5. Weather confidence check
    exp = signal.get("explainability", {})
    weather_conf = exp.get("weather_confidence", 0)
    if weather_conf < MIN_WEATHER_CONFIDENCE:
        return False, f"weather_confidence_too_low:{weather_conf:.2f}"

    # 6. Rejection reasons check
    rejection_reasons = signal.get("rejection_reasons", [])
    if rejection_reasons:
        return False, f"has_rejection_reasons:{','.join(rejection_reasons)}"

    # 7. Ambiguity check (from parse result if available)
    if exp.get("feature_json", {}).get("rejection_reason"):
        return False, "ambiguous_market"

    return True, "signal_actionable"


def create_trade_params(signal: dict[str, Any]) -> dict[str, Any]:
    """Build paper trade parameters from a signal."""
    direction = signal["direction"]
    if direction == "YES":
        entry_price = signal["market_yes_price"]
    else:
        entry_price = 1.0 - signal["market_yes_price"]

    exp = signal.get("explainability", {})

    return {
        "market_id": signal["market_id"],
        "signal_id": signal.get("id", 0),
        "direction": direction,
        "entry_price": entry_price,
        "quantity": 1.0,  # V1: fixed size
        "status": "open",
        "opened_at": datetime.now(timezone.utc),
        "notes": (
            f"Edge: {signal.get('edge', 0):.2%}, "
            f"Confidence: {signal.get('confidence', 'unknown')}, "
            f"Weather conf: {exp.get('weather_confidence', 'N/A'):.2f}"
        ),
    }


def settle_trade(trade: dict[str, Any], resolution_outcome: str) -> dict[str, Any]:
    """Settle a paper trade given the market resolution."""
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
