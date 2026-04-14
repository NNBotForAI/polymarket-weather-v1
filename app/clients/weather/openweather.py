"""OpenWeatherMap provider implementation."""

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.clients.weather.base import WeatherProvider, ProviderCapability

logger = logging.getLogger(__name__)

OWM_BASE = "https://api.openweathermap.org/data/2.5"


class OpenWeatherMapProvider(WeatherProvider):
    """OpenWeatherMap weather provider.

    Capabilities:
    - temperature: SUPPORTED (reliable current and forecast data)
    - rainfall: SUPPORTED (precipitation amounts and probability)
    - wind_speed: LIMITED (surface winds only, not gust/storm data)
    - hurricane: EXPERIMENTAL (surface winds ≠ hurricane data, use NOAA/NHC)
    - snowfall: SUPPORTED (when forecasted)
    - storm: LIMITED (general weather conditions, not storm-specific)
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client = httpx.AsyncClient(timeout=15.0)

    async def get_current_weather(self, location_name: str, lat: float | None = None, lon: float | None = None) -> dict[str, Any] | None:
        """Get current weather from OpenWeatherMap."""
        if not self.api_key:
            logger.warning("OpenWeatherMap: No API key configured")
            return None

        params: dict[str, Any] = {"appid": self.api_key, "units": "imperial"}
        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        else:
            params["q"] = location_name

        try:
            resp = await self._client.get(f"{OWM_BASE}/weather", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.warning("OpenWeatherMap current weather failed for %s: %s", location_name, e)
            return None

        return self._parse_current(data)

    async def get_forecast(self, location_name: str, lat: float | None = None, lon: float | None = None, hours: int = 120) -> dict[str, Any] | None:
        """Get forecast from OpenWeatherMap."""
        if not self.api_key:
            logger.warning("OpenWeatherMap: No API key configured")
            return None

        params: dict[str, Any] = {"appid": self.api_key, "units": "imperial"}
        if lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        else:
            params["q"] = location_name

        try:
            resp = await self._client.get(f"{OWM_BASE}/forecast", params=params)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.warning("OpenWeatherMap forecast failed for %s: %s", location_name, e)
            return None

        return self._parse_forecast(data)

    def get_capabilities(self) -> dict[str, ProviderCapability]:
        """Return OpenWeatherMap capabilities by weather type."""
        return {
            "temperature": ProviderCapability.SUPPORTED,
            "rainfall": ProviderCapability.SUPPORTED,
            "wind_speed": ProviderCapability.LIMITED,
            "hurricane": ProviderCapability.EXPERIMENTAL,
            "snowfall": ProviderCapability.SUPPORTED,
            "storm": ProviderCapability.LIMITED,
            "tornado": ProviderCapability.EXPERIMENTAL,
            "flood": ProviderCapability.EXPERIMENTAL,
            "drought": ProviderCapability.UNSUPPORTED,
            "wildfire": ProviderCapability.UNSUPPORTED,
        }

    def is_available(self) -> tuple[bool, str]:
        """Check if OpenWeatherMap is available."""
        if not self.api_key:
            return False, "No API key configured"
        return True, "Available"

    def _parse_current(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse current weather from OWM response."""
        main = data.get("main", {})
        wind = data.get("wind", {})
        rain = data.get("rain", {})
        weather_list = data.get("weather", [{}])

        return {
            "source": "openweathermap",
            "location_name": data.get("name"),
            "lat": data.get("coord", {}).get("lat"),
            "lon": data.get("coord", {}).get("lon"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "current": {
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
            },
            "forecasts": [],
        }

    def _parse_forecast(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse forecast from OWM response."""
        forecasts = []
        for item in data.get("list", []):
            main = item.get("main", {})
            wind = item.get("wind", {})
            rain = item.get("rain", {})
            weather_list = item.get("weather", [{}])

            forecasts.append({
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
            })

        return {
            "source": "openweathermap",
            "location_name": data.get("city", {}).get("name"),
            "lat": data.get("city", {}).get("coord", {}).get("lat"),
            "lon": data.get("city", {}).get("coord", {}).get("lon"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "current": None,
            "forecasts": forecasts,
        }

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


def get_openweather_provider(api_key: str) -> OpenWeatherMapProvider:
    """Factory function to create OpenWeatherMap provider."""
    return OpenWeatherMapProvider(api_key)
