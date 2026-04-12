"""Weather probability engine — abstract interface for external weather data."""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class WeatherProbabilityEngine:
    """Base class for weather probability estimation.

    In V1 this is a stub that returns conservative estimates.
    Replace with real weather API integration later.
    """

    async def estimate_probability(
        self,
        location: str | None,
        metric: str | None,
        threshold: str | None,
        comparator: str | None,
        target_date: str | None,
    ) -> dict[str, Any]:
        """Estimate P(event) based on weather model.

        Returns dict with: probability_yes, source, model_name, confidence, details.
        """
        # V1 stub: return 0.5 (no edge) with low confidence
        logger.info(
            "Weather probability stub called: location=%s metric=%s threshold=%s",
            location, metric, threshold,
        )
        return {
            "probability_yes": 0.5,
            "source": "stub",
            "model_name": "v1_stub",
            "confidence": "low",
            "details": {
                "note": "V1 stub — replace with real weather API",
                "location": location,
                "metric": metric,
                "threshold": threshold,
                "comparator": comparator,
                "target_date": target_date,
            },
        }


class OpenWeatherMapEngine(WeatherProbabilityEngine):
    """Weather probability via OpenWeatherMap API (placeholder for future use)."""

    async def estimate_probability(
        self,
        location: str | None,
        metric: str | None,
        threshold: str | None,
        comparator: str | None,
        target_date: str | None,
    ) -> dict[str, Any]:
        if not settings.weather_api_key:
            # Fall back to stub
            return await super().estimate_probability(
                location, metric, threshold, comparator, target_date
            )

        # TODO: implement real OWM API call
        # For now, return stub
        return await super().estimate_probability(
            location, metric, threshold, comparator, target_date
        )


def get_weather_engine() -> WeatherProbabilityEngine:
    """Factory to get the configured weather engine."""
    if settings.weather_api_key:
        return OpenWeatherMapEngine()
    return WeatherProbabilityEngine()
