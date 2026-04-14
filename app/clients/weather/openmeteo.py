"""Open-Meteo provider — free weather forecasts, no API key required.

Docs:
  Forecast: https://open-meteo.com/en/docs
  Geocoding: https://open-meteo.com/en/docs/geocoding-api
"""

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.clients.weather.base import WeatherProvider, ProviderCapability

logger = logging.getLogger(__name__)

FORECAST_BASE = "https://api.open-meteo.com/v1"
GEOCODING_BASE = "https://geocoding-api.open-meteo.com/v1"


class OpenMeteoProvider(WeatherProvider):
    """Open-Meteo weather provider — free, no API key.

    Capabilities:
    - temperature: SUPPORTED (hourly + daily, multiple models)
    - rainfall: SUPPORTED (precipitation amount + probability)
    - snowfall: SUPPORTED
    - wind_speed: SUPPORTED (surface wind speed + gusts)
    - hurricane: EXPERIMENTAL (no tropical-cyclone-specific data)
    - storm: LIMITED (general weather codes, not storm-specific)
    - tornado: UNSUPPORTED
    - flood: UNSUPPORTED
    """

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=20.0)

    # ── WeatherProvider interface ──

    async def get_current_weather(
        self, location_name: str, lat: float | None = None, lon: float | None = None
    ) -> dict[str, Any] | None:
        """Get current weather (latest forecast hour)."""
        coords = await self._resolve_coords(location_name, lat, lon)
        if coords is None:
            return None

        lat_val, lon_val = coords
        params = {
            "latitude": lat_val,
            "longitude": lon_val,
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "current": [
                "temperature_2m", "relative_humidity_2m", "apparent_temperature",
                "precipitation", "rain", "snowfall",
                "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m",
                "weather_code", "pressure_msl",
            ],
            "timezone": "auto",
        }

        try:
            resp = await self._client.get(f"{FORECAST_BASE}/forecast", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.warning("Open-Meteo current weather failed for %s: %s", location_name, e)
            return None

        current = data.get("current", {})
        return {
            "source": "openmeteo",
            "location_name": location_name,
            "lat": lat_val,
            "lon": lon_val,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "current": {
                "temp_f": current.get("temperature_2m"),
                "feels_like_f": current.get("apparent_temperature"),
                "humidity_pct": current.get("relative_humidity_2m"),
                "pressure_hpa": current.get("pressure_msl"),
                "wind_speed_mph": current.get("wind_speed_10m"),
                "wind_gust_mph": current.get("wind_gusts_10m"),
                "wind_deg": current.get("wind_direction_10m"),
                "precipitation_in": current.get("precipitation"),
                "rain_in": current.get("rain"),
                "snowfall_in": current.get("snowfall"),
                "weather_code": current.get("weather_code"),
            },
            "forecasts": [],
        }

    async def get_forecast(
        self,
        location_name: str,
        lat: float | None = None,
        lon: float | None = None,
        hours: int = 120,
    ) -> dict[str, Any] | None:
        """Get hourly + daily forecast up to `hours` hours ahead (max 16 days = 384h)."""
        coords = await self._resolve_coords(location_name, lat, lon)
        if coords is None:
            return None

        lat_val, lon_val = coords

        hourly_vars = [
            "temperature_2m", "relative_humidity_2m", "apparent_temperature",
            "precipitation", "rain", "snowfall", "snow_depth",
            "wind_speed_10m", "wind_gusts_10m", "wind_direction_10m",
            "precipitation_probability", "weather_code",
            "temperature_2m_max", "temperature_2m_min",
        ]

        daily_vars = [
            "temperature_2m_max", "temperature_2m_min", "temperature_2m_mean",
            "precipitation_sum", "rain_sum", "snowfall_sum",
            "precipitation_probability_max", "precipitation_hours",
            "wind_speed_10m_max", "wind_gusts_10m_max",
            "weather_code",
        ]

        forecast_days = min(max(hours // 24, 1), 16)

        params = {
            "latitude": lat_val,
            "longitude": lon_val,
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "precipitation_unit": "inch",
            "hourly": hourly_vars,
            "daily": daily_vars,
            "forecast_days": forecast_days,
            "timezone": "auto",
        }

        try:
            resp = await self._client.get(f"{FORECAST_BASE}/forecast", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.warning("Open-Meteo forecast failed for %s: %s", location_name, e)
            return None

        hourly = data.get("hourly", {})
        daily = data.get("daily", {})

        # Parse hourly forecasts (limit to requested hours)
        forecasts = []
        times = hourly.get("time", [])
        limit = min(len(times), hours)
        for i in range(limit):
            forecasts.append({
                "time": times[i],
                "temp_f": self._safe_index(hourly.get("temperature_2m", []), i),
                "feels_like_f": self._safe_index(hourly.get("apparent_temperature", []), i),
                "humidity_pct": self._safe_index(hourly.get("relative_humidity_2m", []), i),
                "wind_speed_mph": self._safe_index(hourly.get("wind_speed_10m", []), i),
                "wind_gust_mph": self._safe_index(hourly.get("wind_gusts_10m", []), i),
                "wind_deg": self._safe_index(hourly.get("wind_direction_10m", []), i),
                "precipitation_in": self._safe_index(hourly.get("precipitation", []), i),
                "rain_in": self._safe_index(hourly.get("rain", []), i),
                "snowfall_in": self._safe_index(hourly.get("snowfall", []), i),
                "precipitation_probability": self._safe_index(hourly.get("precipitation_probability", []), i),
                "weather_code": self._safe_index(hourly.get("weather_code", []), i),
            })

        # Parse daily summaries
        daily_forecasts = []
        daily_times = daily.get("time", [])
        for i in range(len(daily_times)):
            daily_forecasts.append({
                "date": daily_times[i],
                "temp_max_f": self._safe_index(daily.get("temperature_2m_max", []), i),
                "temp_min_f": self._safe_index(daily.get("temperature_2m_min", []), i),
                "temp_mean_f": self._safe_index(daily.get("temperature_2m_mean", []), i),
                "precipitation_sum_in": self._safe_index(daily.get("precipitation_sum", []), i),
                "rain_sum_in": self._safe_index(daily.get("rain_sum", []), i),
                "snowfall_sum_in": self._safe_index(daily.get("snowfall_sum", []), i),
                "precipitation_probability_max": self._safe_index(daily.get("precipitation_probability_max", []), i),
                "precipitation_hours": self._safe_index(daily.get("precipitation_hours", []), i),
                "wind_speed_max_mph": self._safe_index(daily.get("wind_speed_10m_max", []), i),
                "wind_gust_max_mph": self._safe_index(daily.get("wind_gusts_10m_max", []), i),
                "weather_code": self._safe_index(daily.get("weather_code", []), i),
            })

        return {
            "source": "openmeteo",
            "location_name": location_name,
            "lat": lat_val,
            "lon": lon_val,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "current": None,
            "forecasts": forecasts,
            "daily": daily_forecasts,
        }

    def get_capabilities(self) -> dict[str, ProviderCapability]:
        return {
            "temperature": ProviderCapability.SUPPORTED,
            "rainfall": ProviderCapability.SUPPORTED,
            "snowfall": ProviderCapability.SUPPORTED,
            "wind_speed": ProviderCapability.SUPPORTED,
            "hurricane": ProviderCapability.EXPERIMENTAL,
            "storm": ProviderCapability.LIMITED,
            "tornado": ProviderCapability.UNSUPPORTED,
            "flood": ProviderCapability.UNSUPPORTED,
            "drought": ProviderCapability.UNSUPPORTED,
            "wildfire": ProviderCapability.UNSUPPORTED,
        }

    def is_available(self) -> tuple[bool, str]:
        return True, "Free API, no key required"

    # ── Geocoding helper ──

    async def geocode(self, location_name: str) -> tuple[float, float] | None:
        """Geocode a location name to (lat, lon) via Open-Meteo Geocoding API."""
        coords = await self._resolve_coords(location_name)
        return coords

    async def _resolve_coords(
        self, location_name: str, lat: float | None = None, lon: float | None = None
    ) -> tuple[float, float] | None:
        """Return (lat, lon) — use provided coords or geocode."""
        if lat is not None and lon is not None:
            return (lat, lon)

        try:
            resp = await self._client.get(
                f"{GEOCODING_BASE}/search",
                params={"name": location_name, "count": 1, "language": "en", "format": "json"},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results:
                r = results[0]
                return (float(r["latitude"]), float(r["longitude"]))
        except Exception as e:
            logger.warning("Open-Meteo geocoding failed for '%s': %s", location_name, e)

        return None

    async def close(self):
        await self._client.aclose()

    # ── Helpers ──

    @staticmethod
    def _safe_index(lst: list, i: int) -> Any:
        try:
            return lst[i]
        except (IndexError, TypeError):
            return None


def get_openmeteo_provider() -> OpenMeteoProvider:
    return OpenMeteoProvider()
