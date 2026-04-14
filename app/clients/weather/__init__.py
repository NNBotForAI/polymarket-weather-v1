"""Weather providers package — re-exports from weather_v2 for convenience."""

from app.clients.weather_v2 import (
    WeatherClient,
    WeatherData,
    WeatherProvider,
    ProviderCapability,
    get_weather_client,
    get_openweather_provider,
    get_openmeteo_provider,
    get_fallback_geocoding_provider,
    GeocodingProvider,
    ResolvedLocation,
)

__all__ = [
    "WeatherClient",
    "WeatherData",
    "WeatherProvider",
    "ProviderCapability",
    "get_weather_client",
    "get_openweather_provider",
    "get_openmeteo_provider",
    "get_fallback_geocoding_provider",
    "GeocodingProvider",
    "ResolvedLocation",
]
