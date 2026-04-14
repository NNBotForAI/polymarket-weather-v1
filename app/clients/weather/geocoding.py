"""Geocoding provider - location resolution abstraction."""

from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel

class ResolvedLocation(BaseModel):
    """Resolved location with coordinates and metadata."""
    resolved_name: str
    latitude: float | None
    longitude: float | None
    country: str | None
    region: str | None
    resolution_confidence: float  # 0.0-1.0
    ambiguous: bool
    failure_reason: str | None


class GeocodingProvider(ABC):
    """Abstract geocoding provider."""

    @abstractmethod
    async def resolve_location(self, location_name: str) -> ResolvedLocation:
        """Resolve location name to coordinates.

        Args:
            location_name: Human-readable location name

        Returns:
            ResolvedLocation with coordinates and metadata
        """


class FallbackGeocodingProvider(GeocodingProvider):
    """Fallback geocoding using known cities database.

    Uses a built-in dictionary of major cities as a fallback when
    no geocoding API is available.
    """

    def __init__(self):
        self.known_locations = {
            "new york": {"name": "New York", "country": "US", "lat": 40.71, "lon": -74.01},
            "new york city": {"name": "New York", "country": "US", "lat": 40.71, "lon": -74.01},
            "nyc": {"name": "New York", "country": "US", "lat": 40.71, "lon": -74.01},
            "los angeles": {"name": "Los Angeles", "country": "US", "lat": 34.05, "lon": -118.24},
            "la": {"name": "Los Angeles", "country": "US", "lat": 34.05, "lon": -118.24},
            "chicago": {"name": "Chicago", "country": "US", "lat": 41.88, "lon": -87.63},
            "houston": {"name": "Houston", "country": "US", "lat": 29.76, "lon": -95.37},
            "phoenix": {"name": "Phoenix", "country": "US", "lat": 33.45, "lon": -112.07},
            "miami": {"name": "Miami", "country": "US", "lat": 25.76, "lon": -80.19},
            "london": {"name": "London", "country": "GB", "lat": 51.51, "lon": -0.13},
            "paris": {"name": "Paris", "country": "FR", "lat": 48.86, "lon": 2.35},
            "tokyo": {"name": "Tokyo", "country": "JP", "lat": 35.68, "lon": 139.69},
            "seattle": {"name": "Seattle", "country": "US", "lat": 47.61, "lon": -122.33},
            "denver": {"name": "Denver", "country": "US", "lat": 39.74, "lon": -104.99},
            "boston": {"name": "Boston", "country": "US", "lat": 42.36, "lon": -71.06},
            "atlanta": {"name": "Atlanta", "country": "US", "lat": 33.75, "lon": -84.39},
            "dallas": {"name": "Dallas", "country": "US", "lat": 32.78, "lon": -96.80},
            "san francisco": {"name": "San Francisco", "country": "US", "lat": 37.77, "lon": -122.42},
            "sf": {"name": "San Francisco", "country": "US", "lat": 37.77, "lon": -122.42},
            "washington dc": {"name": "Washington", "country": "US", "lat": 38.91, "lon": -77.04},
            "detroit": {"name": "Detroit", "country": "US", "lat": 42.33, "lon": -83.05},
            "minneapolis": {"name": "Minneapolis", "country": "US", "lat": 44.98, "lon": -93.27},
            "florida": {"name": "Florida", "country": "US", "lat": 27.77, "lon": -81.55, "is_region": True},
            "texas": {"name": "Texas", "country": "US", "lat": 31.97, "lon": -99.55, "is_region": True},
            "california": {"name": "California", "country": "US", "lat": 36.78, "lon": -119.42, "is_region": True},
        }

    async def resolve_location(self, location_name: str) -> ResolvedLocation:
        """Resolve location using known cities database."""
        loc_lower = location_name.lower().strip()

        # Check known locations
        for key, loc_data in self.known_locations.items():
            if key == loc_lower:
                is_region = loc_data.get("is_region", False)
                return ResolvedLocation(
                    resolved_name=loc_data["name"],
                    latitude=loc_data["lat"],
                    longitude=loc_data["lon"],
                    country=loc_data["country"],
                    region=loc_data["country"],  # Use country as region for now
                    resolution_confidence=1.0,
                    ambiguous=False,
                    failure_reason=None,
                )

        # Try fuzzy match
        for key, loc_data in self.known_locations.items():
            if key in loc_lower or loc_lower in key:
                is_region = loc_data.get("is_region", False)
                return ResolvedLocation(
                    resolved_name=loc_data["name"],
                    latitude=loc_data["lat"],
                    longitude=loc_data["lon"],
                    country=loc_data["country"],
                    region=loc_data["country"],
                    resolution_confidence=0.7,  # Lower confidence for fuzzy match
                    ambiguous=True,  # Fuzzy match = potential ambiguity
                    failure_reason=None,
                )

        # Not found
        return ResolvedLocation(
            resolved_name=location_name,
            latitude=None,
            longitude=None,
            country=None,
            region=None,
            resolution_confidence=0.0,
            ambiguous=False,
            failure_reason="location_not_in_known_database",
        )


def get_fallback_geocoding_provider() -> FallbackGeocodingProvider:
    """Factory function to create fallback geocoding provider."""
    return FallbackGeocodingProvider()
