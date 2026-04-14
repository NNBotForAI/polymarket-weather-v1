"""Base weather provider abstraction."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

class ProviderCapability(Enum):
    SUPPORTED = "supported"
    LIMITED = "limited"
    EXPERIMENTAL = "experimental"
    UNSUPPORTED = "unsupported"


class WeatherProvider(ABC):
    """Abstract base for all weather data providers.

    All providers must implement these methods to provide a consistent interface
    for the probability engine.
    """

    @abstractmethod
    async def get_current_weather(self, location_name: str, lat: float | None = None, lon: float | None = None) -> dict[str, Any] | None:
        """Get current weather for a location.

        Args:
            location_name: Human-readable location name
            lat: Optional latitude
            lon: Optional longitude

        Returns:
            Structured weather data dict or None if unavailable
        """

    @abstractmethod
    async def get_forecast(self, location_name: str, lat: float | None = None, lon: float | None = None, hours: int = 120) -> dict[str, Any] | None:
        """Get N-hour forecast for a location.

        Args:
            location_name: Human-readable location name
            lat: Optional latitude
            lon: Optional longitude
            hours: Forecast horizon in hours

        Returns:
            Structured forecast data dict or None if unavailable
        """

    @abstractmethod
    def get_capabilities(self) -> dict[str, ProviderCapability]:
        """Return capabilities by weather type.

        Returns:
            Dict mapping weather_type strings to ProviderCapability enum values
        """

    @abstractmethod
    def is_available(self) -> tuple[bool, str]:
        """Check if provider is available (API key configured, etc.).

        Returns:
            Tuple of (available: bool, message: str)
        """
