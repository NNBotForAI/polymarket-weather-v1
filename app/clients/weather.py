"""Weather data client — OpenWeatherMap integration.

Provides structured weather data for the probability engine.
Supports: current weather, 5-day/3-hour forecast.
"""

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

OWM_BASE = "https://api.openweathermap.org/data/2.5"


class WeatherData:
    """Structured weather observation/forecast."""

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
    """Unified weather data client using OpenWeatherMap."""

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or settings.weather_api_key
        self._client = httpx.AsyncClient(timeout=15.0)

    async def get_current(self, location: str, lat: float | None = None, lon: float | None = None) -> WeatherData | None:
        """Get current weather for a location.

        Args:
            location: City name or "lat,lon" string
            lat: Optional latitude
            lon: Optional longitude
        """
        if not self._api_key:
            logger.warning("No weather API key configured")
            return None

        params: dict[str, Any] = {"appid": self._api_key, "units": "imperial"}
        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        else:
            params["q"] = location

        try:
            resp = await self._client.get(f"{OWM_BASE}/weather", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.warning("OWM current weather failed for %s: %s", location, e)
            return None

        current = _parse_current(data)
        return WeatherData(
            source="openweathermap",
            location_name=data.get("name", location),
            lat=data.get("coord", {}).get("lat"),
            lon=data.get("coord", {}).get("lon"),
            fetched_at=datetime.now(timezone.utc),
            current=current,
            raw=data,
        )

    async def get_forecast(self, location: str, lat: float | None = None, lon: float | None = None) -> WeatherData | None:
        """Get 5-day/3-hour forecast for a location."""
        if not self._api_key:
            logger.warning("No weather API key configured")
            return None

        params: dict[str, Any] = {"appid": self._api_key, "units": "imperial"}
        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        else:
            params["q"] = location

        try:
            resp = await self._client.get(f"{OWM_BASE}/forecast", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.warning("OWM forecast failed for %s: %s", location, e)
            return None

        forecasts = [_parse_forecast_item(item) for item in data.get("list", [])]
        current = _parse_current(data) if "main" in data else None

        return WeatherData(
            source="openweathermap",
            location_name=data.get("city", {}).get("name", location),
            lat=data.get("city", {}).get("coord", {}).get("lat"),
            lon=data.get("city", {}).get("coord", {}).get("lon"),
            fetched_at=datetime.now(timezone.utc),
            current=current,
            forecasts=forecasts,
            raw=data,
        )

    async def close(self):
        await self._client.aclose()


def _parse_current(data: dict[str, Any]) -> dict[str, Any]:
    """Parse current weather from OWM response."""
    main = data.get("main", {})
    wind = data.get("wind", {})
    rain = data.get("rain", {})
    weather_list = data.get("weather", [{}])

    return {
        "temp_f": main.get("temp"),
        "feels_like_f": main.get("feels_like"),
        "temp_min_f": main.get("temp_min"),
        "temp_max_f": main.get("temp_max"),
        "humidity_pct": main.get("humidity"),
        "pressure_hpa": main.get("pressure"),
        "wind_speed_mph": wind.get("speed"),
        "wind_gust_mph": wind.get("gust"),
        "wind_deg": wind.get("deg"),
        "rain_1h_in": rain.get("1h"),
        "rain_3h_in": rain.get("3h"),
        "description": weather_list[0].get("description", "") if weather_list else "",
        "dt": data.get("dt"),
    }


def _parse_forecast_item(item: dict[str, Any]) -> dict[str, Any]:
    """Parse a single forecast item (3-hour snapshot)."""
    main = item.get("main", {})
    wind = item.get("wind", {})
    rain = item.get("rain", {})
    weather_list = item.get("weather", [{}])

    return {
        "dt": item.get("dt"),
        "dt_txt": item.get("dt_txt"),
        "temp_f": main.get("temp"),
        "temp_min_f": main.get("temp_min"),
        "temp_max_f": main.get("temp_max"),
        "humidity_pct": main.get("humidity"),
        "wind_speed_mph": wind.get("speed"),
        "wind_gust_mph": wind.get("gust"),
        "wind_deg": wind.get("deg"),
        "rain_3h_in": rain.get("3h"),
        "pop": item.get("pop"),  # probability of precipitation (0-1)
        "description": weather_list[0].get("description", "") if weather_list else "",
    }


def get_weather_client() -> WeatherClient:
    """Factory for weather client."""
    return WeatherClient()
