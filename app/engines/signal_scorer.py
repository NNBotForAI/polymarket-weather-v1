"""Signal scoring engine — compare market price vs weather probability."""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Minimum edge (in percentage points) to generate a signal
MIN_EDGE = 0.05  # 5 percentage points

# Edge thresholds for confidence levels
CONFIDENCE_THRESHOLDS = {
    "high": 0.15,    # 15+ pp edge
    "medium": 0.10,  # 10-15 pp edge
    "low": 0.05,     # 5-10 pp edge
}


def score_signal(
    market_yes_price: float,
    weather_prob: float,
    market_id: int,
    book_snapshot_id: int | None = None,
    weather_model_id: int | None = None,
) -> dict[str, Any]:
    """Generate a signal score comparing market price to weather probability.

    Args:
        market_yes_price: Current market price for Yes (0.0 - 1.0)
        weather_prob: Estimated probability of Yes from weather model (0.0 - 1.0)
        market_id: Market ID
        book_snapshot_id: Optional book snapshot ID
        weather_model_id: Optional weather model run ID

    Returns:
        Signal dict with edge, direction, confidence, recommendation, explainability.
    """
    edge = weather_prob - market_yes_price

    # Determine direction
    if abs(edge) < MIN_EDGE:
        direction = None
        recommendation = "skip"
        confidence = "none"
    elif edge > 0:
        direction = "YES"
        recommendation = "buy_yes"
    else:
        direction = "NO"
        recommendation = "buy_no"

    # Determine confidence
    if recommendation != "skip":
        abs_edge = abs(edge)
        if abs_edge >= CONFIDENCE_THRESHOLDS["high"]:
            confidence = "high"
        elif abs_edge >= CONFIDENCE_THRESHOLDS["medium"]:
            confidence = "medium"
        else:
            confidence = "low"

    # Build explainability
    explainability = {
        "market_price": market_yes_price,
        "weather_probability": weather_prob,
        "edge": edge,
        "edge_pp": round(edge * 100, 2),
        "direction": direction,
        "confidence": confidence,
        "recommendation": recommendation,
        "min_edge_threshold": MIN_EDGE,
        "reasoning": _build_reasoning(market_yes_price, weather_prob, edge, direction),
    }

    return {
        "market_id": market_id,
        "book_snapshot_id": book_snapshot_id,
        "weather_model_id": weather_model_id,
        "market_yes_price": market_yes_price,
        "weather_prob": weather_prob,
        "edge": edge,
        "direction": direction,
        "confidence": confidence,
        "recommendation": recommendation,
        "explainability": explainability,
        "scored_at": datetime.now(timezone.utc),
    }


def _build_reasoning(
    market_price: float,
    weather_prob: float,
    edge: float,
    direction: str | None,
) -> str:
    """Human-readable reasoning for the signal."""
    if direction is None:
        return (
            f"No actionable edge: market at {market_price:.1%}, "
            f"weather model at {weather_prob:.1%}, "
            f"edge {edge:.1%} below threshold."
        )
    return (
        f"Market prices {direction} at {market_price:.1%} but weather model "
        f"estimates {weather_prob:.1%}. Edge: {edge:+.1%}. "
        f"Recommendation: {direction}."
    )
