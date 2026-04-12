"""Weather market parser — identifies weather-related markets and extracts structured data."""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Keywords that indicate a weather market
WEATHER_KEYWORDS = [
    "temperature", "rain", "snow", "hurricane", "tornado", "flood",
    "heat wave", "cold snap", "drought", "wind", "storm", "blizzard",
    "weather", "celsius", "fahrenheit", "inch", "mm of rain",
    "snowfall", "rainfall", "degrees", "°c", "°f",
    "tropical storm", "cyclone", "typhoon", "wildfire",
]

# Patterns for extracting thresholds
THRESHOLD_PATTERNS = [
    (r"(\d+(?:\.\d+)?)\s*°?(?:degrees?|°c|°f|celsius|fahrenheit)", "temperature"),
    (r"(\d+(?:\.\d+)?)\s*(?:inch|inches|mm|cm)\s*(?:of)?\s*(?:rain|snow|rainfall|snowfall)", "precipitation"),
    (r"(?:above|over|exceed|more than|greater than|higher than)\s*(\d+(?:\.\d+)?)", "above"),
    (r"(?:below|under|less than|fewer than|lower than)\s*(\d+(?:\.\d+)?)", "below"),
]

# Comparators
COMPARATOR_MAP = {
    "above": "above",
    "over": "above",
    "exceed": "above",
    "more than": "above",
    "greater than": "above",
    "higher than": "above",
    "below": "below",
    "under": "below",
    "less than": "below",
    "fewer than": "below",
    "lower than": "below",
    "at least": "at_least",
    "at most": "at_most",
    "exactly": "exactly",
    "reach": "reach",
}

# US cities commonly referenced
LOCATION_PATTERNS = [
    r"(?:in|at|for)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",  # "in New York"
    r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:area|city|metro|region)",
]


def is_weather_market(question: str) -> bool:
    """Determine if a market question is weather-related."""
    q_lower = question.lower()
    return any(kw in q_lower for kw in WEATHER_KEYWORDS)


def parse_weather_market(question: str) -> dict[str, Any]:
    """Extract structured weather data from a market question.

    Returns a dict with: is_weather, location, metric, threshold, comparator,
    target_date, is_ambiguous, ambiguity_reason.
    """
    result: dict[str, Any] = {
        "is_weather": False,
        "location": None,
        "metric": None,
        "threshold": None,
        "comparator": None,
        "target_date": None,
        "is_ambiguous": False,
        "ambiguity_reason": None,
    }

    if not is_weather_market(question):
        return result

    result["is_weather"] = True
    q_lower = question.lower()

    # Detect metric
    if any(kw in q_lower for kw in ["temperature", "degree", "°c", "°f", "celsius", "fahrenheit", "hot", "cold"]):
        result["metric"] = "temperature"
    elif any(kw in q_lower for kw in ["rain", "rainfall", "precipitation", "mm of rain"]):
        result["metric"] = "rainfall"
    elif any(kw in q_lower for kw in ["snow", "snowfall", "blizzard"]):
        result["metric"] = "snowfall"
    elif any(kw in q_lower for kw in ["hurricane", "tropical storm", "cyclone", "typhoon"]):
        result["metric"] = "hurricane"
    elif any(kw in q_lower for kw in ["tornado"]):
        result["metric"] = "tornado"
    elif any(kw in q_lower for kw in ["flood"]):
        result["metric"] = "flood"
    elif any(kw in q_lower for kw in ["wildfire", "fire"]):
        result["metric"] = "wildfire"
    elif any(kw in q_lower for kw in ["wind", "storm"]):
        result["metric"] = "wind"

    # Detect threshold
    for pattern, ptype in THRESHOLD_PATTERNS:
        match = re.search(pattern, q_lower)
        if match:
            result["threshold"] = match.group(1)
            if ptype in ("above", "below"):
                result["comparator"] = ptype
            break

    # Detect comparator from text
    if not result["comparator"]:
        for phrase, comp in COMPARATOR_MAP.items():
            if phrase in q_lower:
                result["comparator"] = comp
                break

    # Detect location (simple heuristic)
    for pat in LOCATION_PATTERNS:
        match = re.search(pat, question)
        if match:
            loc = match.group(1).strip()
            # Filter out common false positives
            if loc.lower() not in ("the", "a", "an") and len(loc) > 2:
                result["location"] = loc
                break

    # Detect date references
    month_pattern = r"(january|february|march|april|may|june|july|august|september|october|november|december)\s*(\d{1,2})?,?\s*(\d{4})?"
    date_match = re.search(month_pattern, q_lower)
    if date_match:
        result["target_date"] = date_match.group(0).strip()

    # Check for ambiguity
    ambiguous_signals = [
        "or" in q_lower and q_lower.count("or") > 1,
        not result["metric"],
        "?" not in question,  # not a proper question
    ]
    if any(ambiguous_signals):
        result["is_ambiguous"] = True
        reasons = []
        if not result["metric"]:
            reasons.append("could not determine weather metric")
        if "?" not in question:
            reasons.append("not a question format")
        result["ambiguity_reason"] = "; ".join(reasons) if reasons else "multiple possible interpretations"

    return result
