"""Weather market parser — identifies weather-related markets and extracts structured data.

V1.1: Enhanced output with all fields needed by the probability engine.
Supported types: temperature, rainfall, hurricane/wind.
"""

import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Supported weather types in V1.1
SUPPORTED_WEATHER_TYPES = {"temperature", "rainfall", "hurricane"}

WEATHER_KEYWORDS = [
    "temperature", "rain", "snow", "hurricane", "tornado", "flood",
    "heat wave", "cold snap", "drought", "wind", "storm", "blizzard",
    "weather", "celsius", "fahrenheit", "inch", "mm of rain",
    "snowfall", "rainfall", "degrees", "°c", "°f",
    "tropical storm", "cyclone", "typhoon", "wildfire",
]

COMPARATOR_MAP = {
    "above": "above", "over": "above", "exceed": "above",
    "more than": "above", "greater than": "above", "higher than": "above",
    "at least": "at_least",
    "below": "below", "under": "below", "less than": "below",
    "fewer than": "below", "lower than": "below",
    "at most": "at_most",
    "exactly": "exactly", "reach": "reach",
}

# ── Location ──────────────────────────────────────────────────────────

# Known cities with approximate lat/lon for weather lookups
KNOWN_LOCATIONS: dict[str, dict[str, Any]] = {
    "new york": {"name": "New York", "country": "US", "lat": 40.71, "lon": -74.01},
    "new york city": {"name": "New York", "country": "US", "lat": 40.71, "lon": -74.01},
    "nyc": {"name": "New York", "country": "US", "lat": 40.71, "lon": -74.01},
    "los angeles": {"name": "Los Angeles", "country": "US", "lat": 34.05, "lon": -118.24},
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
    "washington dc": {"name": "Washington", "country": "US", "lat": 38.91, "lon": -77.04},
    "detroit": {"name": "Detroit", "country": "US", "lat": 42.33, "lon": -83.05},
    "minneapolis": {"name": "Minneapolis", "country": "US", "lat": 44.98, "lon": -93.27},
    "florida": {"name": "Florida", "country": "US", "lat": 27.77, "lon": -81.55, "is_region": True},
    "texas": {"name": "Texas", "country": "US", "lat": 31.97, "lon": -99.55, "is_region": True},
    "california": {"name": "California", "country": "US", "lat": 36.78, "lon": -119.42, "is_region": True},
}

LOCATION_PATTERNS = [
    r"(?:in|at|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:area|city|metro|region)",
]

# ── Unit detection ────────────────────────────────────────────────────
TEMP_UNITS = {"°c", "°f", "celsius", "fahrenheit", "degrees"}
RAIN_UNITS = {"inch", "inches", "mm", "cm"}
WIND_UNITS = {"mph", "km/h", "knots", "kts", "knot"}

# ── Date extraction ───────────────────────────────────────────────────
MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}

RELATIVE_DATE_MAP = {
    "today": 0, "tomorrow": 1, "next week": 7, "this weekend": 5,
}


def _detect_location(question: str, q_lower: str) -> dict[str, Any] | None:
    """Detect location from question text."""
    # Check known locations first
    for loc_key, loc_data in KNOWN_LOCATIONS.items():
        if loc_key in q_lower:
            return {**loc_data, "matched_as": "known_city"}

    # Try regex patterns
    for pat in LOCATION_PATTERNS:
        match = re.search(pat, question)
        if match:
            loc = match.group(1).strip()
            if loc.lower() not in ("the", "a", "an", "will", "there", "it") and len(loc) > 2:
                return {"name": loc, "country": "unknown", "lat": None, "lon": None, "matched_as": "regex"}
    return None


def _detect_threshold_and_unit(q_lower: str, metric: str | None) -> tuple[str | None, str | None, str | None]:
    """Extract (threshold_value, threshold_operator, threshold_unit) from question."""
    value: str | None = None
    operator: str | None = None
    unit: str | None = None

    # Temperature patterns
    temp_match = re.search(r"(\d+(?:\.\d+)?)\s*°?\s*(°?[fFcC]|degrees?|celsius|fahrenheit)", q_lower)
    if temp_match and metric == "temperature":
        value = temp_match.group(1)
        raw_unit = temp_match.group(2).lower().strip()
        if raw_unit in ("f", "°f", "fahrenheit"):
            unit = "fahrenheit"
        elif raw_unit in ("c", "°c", "celsius"):
            unit = "celsius"
        else:
            unit = "fahrenheit"  # default for US-centric markets

    # Rainfall patterns
    rain_match = re.search(r"(\d+(?:\.\d+)?)\s*(inch|inches|mm|cm)", q_lower)
    if rain_match and metric in ("rainfall", "snowfall"):
        value = rain_match.group(1)
        raw_unit = rain_match.group(2).lower()
        unit = "inches" if raw_unit in ("inch", "inches") else raw_unit

    # Wind speed patterns
    wind_match = re.search(r"(\d+(?:\.\d+)?)\s*(mph|km/?h|knots?|kts?)", q_lower)
    if wind_match and metric in ("hurricane", "wind"):
        value = wind_match.group(1)
        raw_unit = wind_match.group(2).lower().replace("/", "")
        unit = "mph" if raw_unit in ("mph",) else "kmh" if raw_unit == "kmh" else "knots"

    # Generic number if no unit-specific match
    if value is None:
        num_match = re.search(r"(?:above|over|exceed|more than|greater than|higher than|below|under|less than|lower than|at least|at most|reach)\s*(\d+(?:\.\d+)?)", q_lower)
        if num_match:
            value = num_match.group(1)

    # Detect operator
    for phrase, comp in sorted(COMPARATOR_MAP.items(), key=lambda x: -len(x[0])):
        if phrase in q_lower:
            operator = comp
            break

    return value, operator, unit


def _detect_observation_window(q_lower: str, target_date: str | None) -> tuple[str | None, str | None]:
    """Detect observation window (start, end) from the question."""
    # Relative dates
    for phrase, days_ahead in RELATIVE_DATE_MAP.items():
        if phrase in q_lower:
            start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            end = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
            return start, end

    # Month name
    month_match = re.search(
        r"(january|february|march|april|may|june|july|august|september|october|november|december)\s*(\d{1,2})?,?\s*(\d{4})?",
        q_lower,
    )
    if month_match:
        month_num = MONTHS.get(month_match.group(1), 1)
        day = int(month_match.group(2) or 1)
        year = int(month_match.group(3) or datetime.now(timezone.utc).year)
        date_str = f"{year}-{month_num:02d}-{day:02d}"
        return date_str, date_str

    # "before [date]" or "by [date]"
    by_match = re.search(r"(?:before|by)\s+(\w+\s+\d{1,2},?\s*\d{4})", q_lower)
    if by_match:
        return None, by_match.group(1)

    return None, target_date


def _detect_metric(q_lower: str) -> str | None:
    """Detect weather metric type."""
    if any(kw in q_lower for kw in ["temperature", "degree", "°c", "°f", "celsius", "fahrenheit", "hot", "cold"]):
        return "temperature"
    if any(kw in q_lower for kw in ["rain", "rainfall", "precipitation", "mm of rain"]):
        return "rainfall"
    if any(kw in q_lower for kw in ["snow", "snowfall", "blizzard"]):
        return "snowfall"
    if any(kw in q_lower for kw in ["hurricane", "tropical storm", "cyclone", "typhoon"]):
        return "hurricane"
    if any(kw in q_lower for kw in ["tornado"]):
        return "tornado"
    if any(kw in q_lower for kw in ["flood"]):
        return "flood"
    if any(kw in q_lower for kw in ["wildfire", "fire"]):
        return "wildfire"
    if any(kw in q_lower for kw in ["wind", "storm", "mph", "km/h"]):
        return "wind"
    return None


def is_weather_market(question: str) -> bool:
    """Determine if a market question is weather-related."""
    q_lower = question.lower()
    return any(kw in q_lower for kw in WEATHER_KEYWORDS)


def parse_weather_market(question: str) -> dict[str, Any]:
    """Extract structured weather data from a market question.

    V1.1 output fields:
        is_weather, weather_type, location_name, location_data,
        threshold_operator, threshold_value, threshold_unit,
        observation_window_start, observation_window_end,
        target_date, ambiguity_flags, parse_confidence,
        is_ambiguous, ambiguity_reason,
        (legacy fields for compat: metric, location, threshold, comparator)
    """
    result: dict[str, Any] = {
        "is_weather": False,
        # V1.1 fields
        "weather_type": None,
        "location_name": None,
        "location_data": None,
        "threshold_operator": None,
        "threshold_value": None,
        "threshold_unit": None,
        "observation_window_start": None,
        "observation_window_end": None,
        "ambiguity_flags": [],
        "parse_confidence": "none",
        # Legacy compat
        "is_ambiguous": False,
        "ambiguity_reason": None,
        "metric": None,
        "location": None,
        "threshold": None,
        "comparator": None,
        "target_date": None,
    }

    if not is_weather_market(question):
        return result

    result["is_weather"] = True
    q_lower = question.lower()

    # ── Weather type ──
    weather_type = _detect_metric(q_lower)
    result["weather_type"] = weather_type
    result["metric"] = weather_type  # legacy compat

    # ── Location ──
    loc_data = _detect_location(question, q_lower)
    if loc_data:
        result["location_data"] = loc_data
        result["location_name"] = loc_data["name"]
        result["location"] = loc_data["name"]  # legacy compat

    # ── Threshold + unit + operator ──
    threshold_value, threshold_operator, threshold_unit = _detect_threshold_and_unit(q_lower, weather_type)
    result["threshold_value"] = threshold_value
    result["threshold_operator"] = threshold_operator
    result["threshold_unit"] = threshold_unit
    result["threshold"] = threshold_value  # legacy compat
    result["comparator"] = threshold_operator  # legacy compat

    # ── Observation window ──
    obs_start, obs_end = _detect_observation_window(q_lower, None)
    result["observation_window_start"] = obs_start
    result["observation_window_end"] = obs_end

    # ── Target date ──
    month_match = re.search(
        r"(january|february|march|april|may|june|july|august|september|october|november|december)\s*(\d{1,2})?,?\s*(\d{4})?",
        q_lower,
    )
    if month_match:
        result["target_date"] = month_match.group(0).strip()

    # ── Ambiguity detection ──
    flags: list[str] = []

    if weather_type is None:
        flags.append("unknown_weather_type")
    elif weather_type not in SUPPORTED_WEATHER_TYPES:
        flags.append("unsupported_weather_type")

    if loc_data is None:
        flags.append("missing_location")
    elif loc_data.get("matched_as") == "regex":
        flags.append("unverified_location")
    elif loc_data.get("is_region"):
        flags.append("region_not_city")

    if threshold_value is None:
        flags.append("missing_threshold")

    if threshold_operator is None:
        flags.append("missing_operator")

    if threshold_unit is None and weather_type in ("temperature", "rainfall", "hurricane"):
        flags.append("missing_unit")

    if not result["observation_window_end"]:
        flags.append("missing_time_window")

    if "?" not in question:
        flags.append("not_question_format")

    if "or" in q_lower and q_lower.count("or") > 1:
        flags.append("multiple_conditions")

    result["ambiguity_flags"] = flags
    result["is_ambiguous"] = len(flags) > 0
    if flags:
        result["ambiguity_reason"] = "; ".join(flags)

    # ── Parse confidence ──
    critical_missing = {"unknown_weather_type", "missing_location", "missing_threshold"}
    if critical_missing.intersection(flags):
        result["parse_confidence"] = "low"
    elif len(flags) >= 2:
        result["parse_confidence"] = "medium"
    elif len(flags) == 1:
        result["parse_confidence"] = "medium"
    else:
        result["parse_confidence"] = "high"

    return result
