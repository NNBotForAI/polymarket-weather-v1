"""Weather data client V2 — Backward-compatible wrapper for new provider architecture.

This module re-exports the new provider-based architecture while maintaining
backward compatibility with the old WeatherClient interface.

DEPRECATED: Direct usage of WeatherClient is deprecated. Use provider abstraction instead.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.clients.weather.base import WeatherProvider
from app.clients.weather.openweather import OpenWeatherMapProvider, get_openweather_provider
from app.clients.weather.openmeteo import OpenMeteoProvider, get_openmeteo_provider

logger = logging.getLogger(__name__)


class WeatherData:
    """Structured weather observation/forecast (Legacy wrapper)."""

    def __init__(
        self,
        source: str,
        location_name: str,
        lat: float | None,
        lon: float | None,
        fetched_at: datetime,
        current: dict[str, Any] | None = None,
        forecasts: list[dict[str, Any]] | None = None,
        raw: dict[str, Any] | None = None,
    ):
        self.source = source
        self.location_name = location_name
        self.lat = lat
        self.lon = lon
        self.fetched_at = fetched_at
        self.current = current
        self.forecasts = forecasts or []
        self.raw = raw

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "location_name": self.location_name,
            "lat": self.lat,
            "lon": self.lon,
            "fetched_at": self.fetched_at.isoformat(),
            "current": self.current,
            "forecast_count": len(self.forecasts),
        }


class WeatherClient:
    """Unified weather data client using OpenWeatherMap (Legacy wrapper).

    DEPRECATED: Use WeatherProvider interface instead.
    This class wraps the new OpenWeatherMapProvider for backward compatibility.
    """

    def __init__(self, api_key: str | None = None, provider: WeatherProvider | None = None):
        if provider:
            self._provider = provider
        elif api_key and api_key != "your-api-key-here":
            self._api_key = api_key
            self._provider = OpenWeatherMapProvider(self._api_key)
        else:
            # Default to Open-Meteo (free, no API key)
            self._api_key = None
            self._provider = get_openmeteo_provider()

    async def get_current(self, location: str, lat: float | None = None, lon: float | None = None) -> WeatherData | None:
        """Get current weather for a location (Legacy wrapper)."""
        data = await self._provider.get_current_weather(location, lat, lon)
        if data is None:
            return None

        return WeatherData(
            source=data["source"],
            location_name=data["location_name"],
            lat=data["lat"],
            lon=data["lon"],
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
            current=data["current"],
            raw=data,
        )

    async def get_forecast(self, location: str, lat: float | None = None, lon: float | None = None) -> WeatherData | None:
        """Get 5-day/3-hour forecast for a location (Legacy wrapper)."""
        data = await self._provider.get_forecast(location, lat, lon)
        if data is None:
            return None

        return WeatherData(
            source=data["source"],
            location_name=data["location_name"],
            lat=data["lat"],
            lon=data["lon"],
            fetched_at=datetime.fromisoformat(data["fetched_at"]),
            current=data["current"],
            forecasts=data["forecasts"],
            raw=data,
        )

    async def close(self):
        """Close the underlying provider if it has a close method."""
        if hasattr(self._provider, "close"):
            await self._provider.close()


def get_weather_client() -> WeatherClient:
    """Factory for weather client (Legacy wrapper)."""
    return WeatherClient()


# ── Re-exports for new architecture ──

from app.clients.weather.base import WeatherProvider, ProviderCapability
from app.clients.weather.openweather import get_openweather_provider
from app.clients.weather.openmeteo import OpenMeteoProvider, get_openmeteo_provider
from app.clients.weather.geocoding import GeocodingProvider, ResolvedLocation, get_fallback_geocoding_provider

__all__ = [
    # Legacy (deprecated)
    "WeatherClient",
    "WeatherData",
    "get_weather_client",
    # New architecture
    "WeatherProvider",
    "ProviderCapability",
    "OpenWeatherMapProvider",
    "get_openweather_provider",
    "OpenMeteoProvider",
    "get_openmeteo_provider",
    "GeocodingProvider",
    "ResolvedLocation",
    "get_fallback_geocoding_provider",
]
