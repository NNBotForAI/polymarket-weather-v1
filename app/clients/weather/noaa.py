"""NOAA weather provider stub.

This is a stub implementation for future NOAA integration.

Planned capabilities:
- storm: SUPPORTED (severe weather alerts, storm tracking)
- severe weather: SUPPORTED (watches, warnings, advisories)
- hurricane: SUPPORTED (specialized hurricane data from NWS)
- tropical cyclone: SUPPORTED (official track and intensity forecasts)

Implementation TODO:
- Integrate with NOAA Weather API
- Support NWS alerts and warnings
- Add severe weather event tracking
"""

import logging
from typing import Any

from app.clients.weather.base import WeatherProvider, ProviderCapability

logger = logging.getLogger(__name__)


class NOAAProvider(WeatherProvider):
    """NOAA weather provider (STUB - not implemented).

    NOTE: This is a structural stub. The actual implementation requires
    NOAA API integration and is planned for future development.
    """

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        raise NotImplementedError(
            "NOAA provider is a stub. Implementation requires NOAA API integration. "
            "Planned capabilities: storm tracking, severe weather alerts, hurricane data."
        )

    async def get_current_weather(self, location_name: str, lat: float | None = None, lon: float | None = None) -> dict[str, Any] | None:
        """Get current weather from NOAA (STUB)."""
        raise NotImplementedError("NOAA provider is not implemented yet")

    async def get_forecast(self, location_name: str, lat: float | None = None, lon: float | None = None, hours: int = 120) -> dict[str, Any] | None:
        """Get forecast from NOAA (STUB)."""
        raise NotImplementedError("NOAA provider is not implemented yet")

    def get_capabilities(self) -> dict[str, ProviderCapability]:
        """Return NOAA capabilities (planned).

        NOTE: These are planned capabilities. The provider is not implemented.
        """
        return {
            "storm": ProviderCapability.SUPPORTED,
            "severe weather": ProviderCapability.SUPPORTED,
            "hurricane": ProviderCapability.SUPPORTED,
            "tropical cyclone": ProviderCapability.SUPPORTED,
            "temperature": ProviderCapability.SUPPORTED,
            "rainfall": ProviderCapability.SUPPORTED,
            "wind_speed": ProviderCapability.SUPPORTED,
            "snowfall": ProviderCapability.SUPPORTED,
        }

    def is_available(self) -> tuple[bool, str]:
        """NOAA is not available (STUB)."""
        return False, "NOAA provider is a stub and not implemented"


def get_noaa_provider(api_key: str | None = None) -> NOAAProvider:
    """Factory function (STUB)."""
    return NOAAProvider(api_key)
