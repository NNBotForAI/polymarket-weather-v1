"""Signal scoring engine V1.1 — compare market price vs weather probability.

Consumes the new WeatherProbabilityResult with structured rejection reasons.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.engines.weather_probability import WeatherProbabilityResult

logger = logging.getLogger(__name__)

# ── Thresholds ────────────────────────────────────────────────────────
MIN_EDGE = 0.05          # 5pp minimum edge
MIN_CONFIDENCE = 0.3     # minimum weather confidence to trade
MAX_SPREAD = 0.10        # maximum acceptable spread
MAX_FRESHNESS_MIN = 360  # reject if data older than 6 hours
EDGE_THRESHOLDS = {"high": 0.15, "medium": 0.10, "low": 0.05}


def score_signal(
    market_yes_price: float,
    weather_result: WeatherProbabilityResult,
    market_id: int,
    spread: float | None = None,
    liquidity: float | None = None,
    book_snapshot_id: int | None = None,
    weather_model_id: int | None = None,
    parse_confidence: str | None = None,
) -> dict[str, Any]:
    """Generate a signal score from market price and weather probability.

    Returns dict with: edge, direction, confidence, recommendation,
    rejection_reasons (if any), explainability.
    """
    rejection_reasons: list[str] = []
    true_prob = weather_result.true_prob_raw
    weather_confidence = weather_result.confidence_score

    # ── Pre-flight checks (structured rejection) ──

    # Check if weather engine rejected the estimate
    if weather_result.source == "rejected":
        rejection_reasons.append(weather_result.feature_json.get("rejection_reason", "weather_engine_rejected"))

    # Parser confidence
    if parse_confidence == "low":
        rejection_reasons.append("parser_confidence_too_low")

    # Stale data
    if weather_result.data_freshness_minutes and weather_result.data_freshness_minutes > MAX_FRESHNESS_MIN:
        rejection_reasons.append("stale_weather_data")

    # Unsupported weather type
    if weather_result.model_notes and "REJECTED" in weather_result.model_notes:
        if "unsupported" not in str(rejection_reasons):
            rejection_reasons.append("unsupported_weather_type")

    # Weather confidence too low
    if weather_confidence < MIN_CONFIDENCE:
        rejection_reasons.append("insufficient_weather_confidence")

    # Spread check
    if spread is not None and spread > MAX_SPREAD:
        rejection_reasons.append("spread_too_wide")

    # Liquidity check
    if liquidity is not None and liquidity < 1000:
        rejection_reasons.append("insufficient_liquidity")

    # ── Calculate edge ──
    edge = true_prob - market_yes_price

    # Edge check
    if abs(edge) < MIN_EDGE:
        rejection_reasons.append("edge_too_small")

    # ── Determine action ──
    if rejection_reasons:
        direction = None
        recommendation = "skip"
        confidence = "none"
    elif edge > 0:
        direction = "YES"
        recommendation = "buy_yes"
        abs_edge = abs(edge)
        if abs_edge >= EDGE_THRESHOLDS["high"]:
            confidence = "high"
        elif abs_edge >= EDGE_THRESHOLDS["medium"]:
            confidence = "medium"
        else:
            confidence = "low"
    else:
        direction = "NO"
        recommendation = "buy_no"
        abs_edge = abs(edge)
        if abs_edge >= EDGE_THRESHOLDS["high"]:
            confidence = "high"
        elif abs_edge >= EDGE_THRESHOLDS["medium"]:
            confidence = "medium"
        else:
            confidence = "low"

    # Adjust confidence by weather confidence
    if confidence not in ("none",) and weather_confidence < 0.6:
        confidence = "low"

    # ── Build explainability ──
    explainability = {
        "market_price": market_yes_price,
        "weather_probability": true_prob,
        "weather_confidence": weather_confidence,
        "edge": round(edge, 4),
        "edge_pp": round(edge * 100, 2),
        "direction": direction,
        "confidence": confidence,
        "recommendation": recommendation,
        "rejection_reasons": rejection_reasons,
        "weather_source": weather_result.source,
        "weather_type": weather_result.weather_type,
        "data_freshness_minutes": weather_result.data_freshness_minutes,
        "spread": spread,
        "liquidity": liquidity,
        "model_notes": weather_result.model_notes,
        "feature_json": weather_result.feature_json,
    }

    return {
        "market_id": market_id,
        "book_snapshot_id": book_snapshot_id,
        "weather_model_id": weather_model_id,
        "market_yes_price": market_yes_price,
        "weather_prob": true_prob,
        "edge": round(edge, 4),
        "direction": direction,
        "confidence": confidence,
        "recommendation": recommendation,
        "rejection_reasons": rejection_reasons,
        "explainability": explainability,
        "scored_at": datetime.now(timezone.utc),
    }


# Backward-compatible wrapper for tests that pass raw floats
def score_signal_simple(
    market_yes_price: float,
    weather_prob: float,
    market_id: int,
    confidence: float = 0.8,
    book_snapshot_id: int | None = None,
    weather_model_id: int | None = None,
) -> dict[str, Any]:
    """Simple wrapper that creates a WeatherProbabilityResult from floats."""
    result = WeatherProbabilityResult(
        true_prob_raw=weather_prob,
        confidence_score=confidence,
        data_freshness_minutes=10.0,
        model_notes="simple wrapper",
        feature_json={"method": "simple"},
        source="direct",
        weather_type="unknown",
    )
    return score_signal(
        market_yes_price=market_yes_price,
        weather_result=result,
        market_id=market_id,
        book_snapshot_id=book_snapshot_id,
        weather_model_id=weather_model_id,
    )
