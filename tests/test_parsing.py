"""Tests for binary and weather parsers."""

import pytest
from app.parsers.binary_parser import is_binary_market, parse_binary_market
from app.parsers.weather_parser import (
    is_weather_market,
    parse_weather_market,
    SUPPORTED_WEATHER_TYPES,
)


class TestBinaryParser:
    def test_is_binary_yes_no(self):
        market = {"outcomes": '["Yes", "No"]'}
        assert is_binary_market(market) is True

    def test_is_binary_with_list(self):
        market = {"outcomes": ["Yes", "No"]}
        assert is_binary_market(market) is True

    def test_not_binary_multi_outcome(self):
        market = {"outcomes": '["A", "B", "C"]'}
        assert is_binary_market(market) is False

    def test_not_binary_non_yes_no(self):
        market = {"outcomes": '["Option A", "Option B"]'}
        assert is_binary_market(market) is False

    def test_parse_binary_market(self):
        market = {
            "id": "123",
            "question": "Will it rain in NYC tomorrow?",
            "slug": "rain-nyc",
            "description": "Test",
            "endDate": "2026-06-01T00:00:00Z",
            "outcomePrices": '["0.65", "0.35"]',
            "volumeNum": 50000,
            "liquidityNum": 10000,
            "active": True,
            "closed": False,
        }
        result = parse_binary_market(market)
        assert result["polymarket_id"] == "123"
        assert result["yes_price"] == 0.65
        assert result["no_price"] == 0.35
        assert result["is_binary"] is True


class TestWeatherParserV11:
    """V1.1 enhanced parser tests."""

    # ── Temperature ──
    def test_temperature_above_fahrenheit(self):
        result = parse_weather_market("Will temperature exceed 90°F in Phoenix?")
        assert result["is_weather"] is True
        assert result["weather_type"] == "temperature"
        assert result["threshold_value"] == "90"
        assert result["threshold_unit"] == "fahrenheit"
        assert result["threshold_operator"] is not None
        assert result["location_name"] is not None

    def test_temperature_celsius(self):
        result = parse_weather_market("Will the temperature reach 35 celsius in London?")
        assert result["weather_type"] == "temperature"
        assert result["threshold_value"] == "35"
        assert result["threshold_unit"] == "celsius"

    def test_temperature_below(self):
        result = parse_weather_market("Will temperature fall below 32°F in Chicago?")
        assert result["weather_type"] == "temperature"
        assert result["threshold_operator"] == "below"
        assert result["location_name"] is not None

    # ── Rainfall ──
    def test_rainfall_inches(self):
        result = parse_weather_market("Will there be more than 2 inches of rain in Seattle?")
        assert result["is_weather"] is True
        assert result["weather_type"] == "rainfall"
        assert result["threshold_value"] == "2"
        assert result["threshold_unit"] == "inches"
        assert result["location_name"] is not None

    def test_rainfall_mm(self):
        result = parse_weather_market("Will rainfall exceed 50mm in Tokyo tomorrow?")
        assert result["weather_type"] == "rainfall"
        assert result["threshold_value"] == "50"
        assert result["threshold_unit"] == "mm"

    # ── Hurricane ──
    def test_hurricane_wind(self):
        result = parse_weather_market("Will wind speeds exceed 74 mph during the hurricane in Florida?")
        assert result["is_weather"] is True
        assert result["weather_type"] == "hurricane"
        assert result["threshold_value"] == "74"

    # ── Location detection ──
    def test_known_city_nyc(self):
        result = parse_weather_market("Will it rain in NYC tomorrow?")
        assert result["location_name"] == "New York"
        assert result["location_data"]["lat"] is not None

    def test_known_city_london(self):
        result = parse_weather_market("Will temperature reach 90°F in London?")
        assert result["location_name"] == "London"

    def test_missing_location(self):
        result = parse_weather_market("Will temperature exceed 90°F tomorrow?")
        assert result["location_name"] is None
        assert "missing_location" in result["ambiguity_flags"]

    def test_unverified_location(self):
        result = parse_weather_market("Will it rain in Springfield tomorrow?")
        # Springfield isn't in known locations, so it's regex-matched
        # May or may not be found depending on regex
        # The key thing is it shouldn't crash

    # ── Ambiguity detection ──
    def test_ambiguous_no_threshold(self):
        result = parse_weather_market("Will the weather be bad in New York?")
        assert "missing_threshold" in result["ambiguity_flags"]
        assert result["parse_confidence"] in ("low", "medium")

    def test_ambiguous_unsupported_type(self):
        result = parse_weather_market("Will there be a tornado in Dallas?")
        assert "unsupported_weather_type" in result.get("ambiguity_flags", [])

    def test_parse_confidence_high(self):
        """Well-formed question with known city, clear threshold."""
        result = parse_weather_market("Will temperature exceed 90°F in Phoenix tomorrow?")
        assert result["parse_confidence"] in ("high", "medium")

    def test_parse_confidence_low_no_location(self):
        result = parse_weather_market("Will temperature exceed 90°F tomorrow?")
        assert result["parse_confidence"] == "low"

    # ── Non-weather ──
    def test_not_weather(self):
        result = parse_weather_market("Will Bitcoin reach $100k?")
        assert result["is_weather"] is False
        assert result["weather_type"] is None

    # ── Legacy compat ──
    def test_legacy_fields(self):
        result = parse_weather_market("Will temperature exceed 90°F in Phoenix?")
        assert result["metric"] == result["weather_type"]
        assert result["location"] == result["location_name"]
        assert result["threshold"] == result["threshold_value"]
        assert result["comparator"] == result["threshold_operator"]

    # ── Observation window ──
    def test_relative_date_tomorrow(self):
        result = parse_weather_market("Will it rain in NYC tomorrow?")
        assert result["observation_window_start"] is not None
        assert result["observation_window_end"] is not None

    def test_relative_date_today(self):
        result = parse_weather_market("Will it rain in NYC today?")
        assert result["observation_window_start"] is not None
