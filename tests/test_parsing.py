"""Tests for binary and weather parsers."""

import pytest
from app.parsers.binary_parser import is_binary_market, parse_binary_market
from app.parsers.weather_parser import is_weather_market, parse_weather_market


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


class TestWeatherParser:
    def test_is_weather_temperature(self):
        assert is_weather_market("Will the temperature exceed 90°F in Phoenix?") is True

    def test_is_weather_rain(self):
        assert is_weather_market("Will it rain in London tomorrow?") is True

    def test_is_weather_hurricane(self):
        assert is_weather_market("Will a hurricane hit Florida?") is True

    def test_not_weather(self):
        assert is_weather_market("Will Bitcoin reach $100k?") is False

    def test_parse_temperature(self):
        result = parse_weather_market("Will temperature exceed 90°F in Phoenix?")
        assert result["is_weather"] is True
        assert result["metric"] == "temperature"
        assert result["threshold"] == "90"

    def test_parse_rain(self):
        result = parse_weather_market("Will there be more than 2 inches of rain in Seattle?")
        assert result["is_weather"] is True
        assert result["metric"] == "rainfall"
        assert result["threshold"] == "2"

    def test_parse_non_weather(self):
        result = parse_weather_market("Will Trump win 2028?")
        assert result["is_weather"] is False

    def test_parse_location(self):
        result = parse_weather_market("Will it snow in New York City in December?")
        assert result["is_weather"] is True
        assert result["location"] is not None
