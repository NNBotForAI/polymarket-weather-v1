"""NHC (National Hurricane Center) weather provider stub.

This is a stub implementation for future NHC integration.

Planned capabilities:
- hurricane: SUPPORTED (official hurricane tracks, advisories, forecasts)
- tropical cyclone: SUPPORTED (official tropical cyclone data)
- tropical storm: SUPPORTED (tropical storm tracking and forecasts)

Implementation TODO:
- Integrate with NHC API (official hurricane data source)
- Support hurricane track and intensity forecasts
- Add real-time tropical cyclone monitoring
"""

import logging
from typing import Any

from app.clients.weather.base import WeatherProvider, ProviderCapability

logger = logging.getLogger(__name__)


class NHCProvider(WeatherProvider):
    """National Hurricane Center provider (STUB - not implemented).

    NOTE: This is a structural stub. The actual implementation requires
    NHC API integration and is planned for future development.

    Why NHC is critical for hurricane markets:
    - OWM provides surface wind speeds only (e.g., 25-40 mph)
    - Real hurricane winds are 74+ mph (Category 1) and can exceed 150 mph
    - OWM cannot distinguish between a storm and a hurricane
    - NHC provides official hurricane-specific data: tracks, intensity, advisories

    Example limitation:
    - OWM might show "wind speed: 35 mph" (just windy weather)
    - Actual hurricane data would show: "Category 3, 115 mph, tracking toward Florida"
    """

    def __init__(self):
        raise NotImplementedError(
            "NHC provider is a stub. Implementation requires NHC API integration. "
            "Critical for accurate hurricane probability estimation. "
            "OWM surface wind data is insufficient for hurricane markets."
        )

    async def get_current_weather(self, location_name: str, lat: float | None = None, lon: float | None = None) -> dict[str, Any] | None:
        """Get current hurricane data from NHC (STUB)."""
        raise NotImplementedError("NHC provider is not implemented yet")

    async def get_forecast(self, location_name: str, lat: float | None = None, lon: float | None = None, hours: int = 120) -> dict[str, Any] | None:
        """Get hurricane forecast from NHC (STUB)."""
        raise NotImplementedError("NHC provider is not implemented yet")

    def get_capabilities(self) -> dict[str, ProviderCapability]:
        """Return NHC capabilities (planned).

        NOTE: These are planned capabilities. The provider is not implemented.
        """
        return {
            "hurricane": ProviderCapability.SUPPORTED,
            "tropical cyclone": ProviderCapability.SUPPORTED,
            "tropical storm": ProviderCapability.SUPPORTED,
        }

    def is_available(self) -> tuple[bool, str]:
        """NHC is not available (STUB)."""
        return False, "NHC provider is a stub and not implemented"


def get_nhc_provider() -> NHCProvider:
    """Factory function (STUB)."""
    return NHCProvider()
