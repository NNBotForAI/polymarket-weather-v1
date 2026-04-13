"""Tests for weather probability engine V1.1."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.engines.weather_probability import (
    WeatherProbabilityEngine,
    WeatherProbabilityResult,
    get_weather_engine,
)
from app.clients.weather import WeatherData


def _make_forecast_data(
    temps_f: list[float] | None = None,
    rain_3h_in: list[float | None] | None = None,
    pops: list[float | None] | None = None,
    wind_mph: list[float | None] | None = None,
    gust_mph: list[float | None] | None = None,
    location: str = "Phoenix",
) -> WeatherData:
    """Create mock forecast data."""
    forecasts = []
    count = max(len(temps_f or []), len(pops or []), len(wind_mph or []), 8)
    for i in range(count):
        item = {
            "dt": int((datetime.now(timezone.utc) + timedelta(hours=3 * i)).timestamp()),
            "dt_txt": "test",
        }
        if temps_f and i < len(temps_f):
            item["temp_f"] = temps_f[i]
        if rain_3h_in and i < len(rain_3h_in):
            item["rain_3h_in"] = rain_3h_in[i]
        if pops and i < len(pops):
            item["pop"] = pops[i]
        if wind_mph and i < len(wind_mph):
            item["wind_speed_mph"] = wind_mph[i]
        if gust_mph and i < len(gust_mph):
            item["wind_gust_mph"] = gust_mph[i]
        forecasts.append(item)

    return WeatherData(
        source="mock",
        location_name=location,
        lat=33.45,
        lon=-112.07,
        fetched_at=datetime.now(timezone.utc),
        current={"temp_f": 95.0},
        forecasts=forecasts,
    )


class TestTemperatureEstimation:
    @pytest.mark.asyncio
    async def test_above_threshold_high_probability(self):
        """All forecasts above threshold → high probability."""
        data = _make_forecast_data(temps_f=[95, 97, 93, 94, 96, 92, 95, 98])
        client = AsyncMock()
        client.get_forecast = AsyncMock(return_value=data)
        engine = WeatherProbabilityEngine(client=client)

        parse = {
            "is_weather": True, "weather_type": "temperature",
            "location_name": "Phoenix", "threshold_value": "90",
            "threshold_operator": "above", "threshold_unit": "fahrenheit",
            "parse_confidence": "high", "location_data": {"lat": 33.45, "lon": -112.07},
        }
        result = await engine.estimate_probability(parse)
        assert result.true_prob_raw >= 0.8
        assert result.confidence_score > 0.5
        assert result.source == "openweathermap_forecast"
        assert result.weather_type == "temperature"

    @pytest.mark.asyncio
    async def test_below_threshold_low_probability(self):
        """No forecasts above threshold → low probability."""
        data = _make_forecast_data(temps_f=[70, 72, 68, 71, 69, 73, 70, 72])
        client = AsyncMock()
        client.get_forecast = AsyncMock(return_value=data)
        engine = WeatherProbabilityEngine(client=client)

        parse = {
            "is_weather": True, "weather_type": "temperature",
            "location_name": "Seattle", "threshold_value": "90",
            "threshold_operator": "above", "threshold_unit": "fahrenheit",
            "parse_confidence": "high", "location_data": {"lat": 47.61, "lon": -122.33},
        }
        result = await engine.estimate_probability(parse)
        assert result.true_prob_raw < 0.2
        assert result.confidence_score > 0.3  # high z-score → confident

    @pytest.mark.asyncio
    async def test_mixed_forecasts(self):
        """Some above, some below → moderate probability."""
        data = _make_forecast_data(temps_f=[95, 85, 92, 88, 91, 87, 90, 89])
        client = AsyncMock()
        client.get_forecast = AsyncMock(return_value=data)
        engine = WeatherProbabilityEngine(client=client)

        parse = {
            "is_weather": True, "weather_type": "temperature",
            "location_name": "Dallas", "threshold_value": "90",
            "threshold_operator": "above", "threshold_unit": "fahrenheit",
            "parse_confidence": "high", "location_data": {"lat": 32.78, "lon": -96.80},
        }
        result = await engine.estimate_probability(parse)
        assert 0.1 < result.true_prob_raw < 0.9
        assert result.feature_json["method"] == "forecast_hit_ratio"

    @pytest.mark.asyncio
    async def test_celsius_conversion(self):
        """Celsius threshold is converted to Fahrenheit."""
        data = _make_forecast_data(temps_f=[100, 102, 98, 101, 99, 100, 103, 97])
        client = AsyncMock()
        client.get_forecast = AsyncMock(return_value=data)
        engine = WeatherProbabilityEngine(client=client)

        parse = {
            "is_weather": True, "weather_type": "temperature",
            "location_name": "Phoenix", "threshold_value": "35",
            "threshold_operator": "above", "threshold_unit": "celsius",
            "parse_confidence": "high", "location_data": {"lat": 33.45, "lon": -112.07},
        }
        result = await engine.estimate_probability(parse)
        # 35°C = 95°F, all forecasts should be above
        assert result.true_prob_raw >= 0.7


class TestRainfallEstimation:
    @pytest.mark.asyncio
    async def test_high_rain_probability(self):
        data = _make_forecast_data(
            pops=[0.9, 0.8, 0.7, 0.85, 0.9, 0.75],
            rain_3h_in=[0.5, 0.3, 0.2, 0.4, 0.6, 0.3],
        )
        client = AsyncMock()
        client.get_forecast = AsyncMock(return_value=data)
        engine = WeatherProbabilityEngine(client=client)

        parse = {
            "is_weather": True, "weather_type": "rainfall",
            "location_name": "Seattle", "threshold_value": "1",
            "threshold_operator": "above", "threshold_unit": "inches",
            "parse_confidence": "high", "location_data": {"lat": 47.61, "lon": -122.33},
        }
        result = await engine.estimate_probability(parse)
        assert result.true_prob_raw > 0.5
        assert result.weather_type == "rainfall"

    @pytest.mark.asyncio
    async def test_no_rain_forecast(self):
        data = _make_forecast_data(pops=[0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        client = AsyncMock()
        client.get_forecast = AsyncMock(return_value=data)
        engine = WeatherProbabilityEngine(client=client)

        parse = {
            "is_weather": True, "weather_type": "rainfall",
            "location_name": "Phoenix", "threshold_value": "1",
            "threshold_operator": "above", "threshold_unit": "inches",
            "parse_confidence": "high", "location_data": {"lat": 33.45, "lon": -112.07},
        }
        result = await engine.estimate_probability(parse)
        assert result.true_prob_raw < 0.3


class TestHurricaneEstimation:
    @pytest.mark.asyncio
    async def test_wind_below_threshold(self):
        """Normal winds should give very low hurricane probability."""
        data = _make_forecast_data(wind_mph=[10, 15, 12, 8, 14, 11, 13, 9])
        client = AsyncMock()
        client.get_forecast = AsyncMock(return_value=data)
        engine = WeatherProbabilityEngine(client=client)

        parse = {
            "is_weather": True, "weather_type": "hurricane",
            "location_name": "Miami", "threshold_value": "74",
            "threshold_operator": "above", "threshold_unit": "mph",
            "parse_confidence": "medium", "location_data": {"lat": 25.76, "lon": -80.19},
        }
        result = await engine.estimate_probability(parse)
        assert result.true_prob_raw < 0.1
        assert result.confidence_score <= 0.4  # Capped for hurricane

    @pytest.mark.asyncio
    async def test_hurricane_low_confidence_limitation(self):
        """Hurricane estimates should always have low confidence (limitation)."""
        data = _make_forecast_data(wind_mph=[80, 90, 85, 95])
        client = AsyncMock()
        client.get_forecast = AsyncMock(return_value=data)
        engine = WeatherProbabilityEngine(client=client)

        parse = {
            "is_weather": True, "weather_type": "hurricane",
            "location_name": "Miami", "threshold_value": "74",
            "threshold_operator": "above", "threshold_unit": "mph",
            "parse_confidence": "high", "location_data": {"lat": 25.76, "lon": -80.19},
        }
        result = await engine.estimate_probability(parse)
        assert result.confidence_score <= 0.4  # Hard cap
        assert "LIMITATION" in result.model_notes


class TestRejectionCases:
    @pytest.mark.asyncio
    async def test_missing_location(self):
        engine = WeatherProbabilityEngine()
        parse = {
            "is_weather": True, "weather_type": "temperature",
            "location_name": None, "threshold_value": "90",
            "threshold_operator": "above", "threshold_unit": "fahrenheit",
            "parse_confidence": "low",
        }
        result = await engine.estimate_probability(parse)
        assert result.source == "rejected"
        assert result.confidence_score == 0.0

    @pytest.mark.asyncio
    async def test_missing_threshold(self):
        engine = WeatherProbabilityEngine()
        parse = {
            "is_weather": True, "weather_type": "temperature",
            "location_name": "Phoenix", "threshold_value": None,
            "threshold_operator": "above", "threshold_unit": "fahrenheit",
            "parse_confidence": "medium", "location_data": {"lat": 33.45, "lon": -112.07},
        }
        result = await engine.estimate_probability(parse)
        assert result.source == "rejected"

    @pytest.mark.asyncio
    async def test_unsupported_weather_type(self):
        engine = WeatherProbabilityEngine()
        parse = {
            "is_weather": True, "weather_type": "tornado",
            "location_name": "Dallas", "threshold_value": "5",
            "parse_confidence": "medium",
        }
        result = await engine.estimate_probability(parse)
        assert result.source == "rejected"

    @pytest.mark.asyncio
    async def test_no_forecast_data(self):
        client = AsyncMock()
        client.get_forecast = AsyncMock(return_value=None)
        engine = WeatherProbabilityEngine(client=client)

        parse = {
            "is_weather": True, "weather_type": "temperature",
            "location_name": "Phoenix", "threshold_value": "90",
            "threshold_operator": "above", "threshold_unit": "fahrenheit",
            "parse_confidence": "high", "location_data": {"lat": 33.45, "lon": -112.07},
        }
        result = await engine.estimate_probability(parse)
        assert result.source == "rejected"
        assert "insufficient" in result.model_notes.lower()

    @pytest.mark.asyncio
    async def test_parser_confidence_too_low(self):
        engine = WeatherProbabilityEngine()
        parse = {
            "is_weather": True, "weather_type": "temperature",
            "location_name": "Phoenix", "threshold_value": "90",
            "parse_confidence": "low",
        }
        result = await engine.estimate_probability(parse)
        assert result.source == "rejected"

    @pytest.mark.asyncio
    async def test_ambiguous_market_no_high_confidence(self):
        """Ambiguous markets should not produce fake high confidence."""
        data = _make_forecast_data(temps_f=[95, 97, 93, 94, 96, 92, 95, 98])
        client = AsyncMock()
        client.get_forecast = AsyncMock(return_value=data)
        engine = WeatherProbabilityEngine(client=client)

        parse = {
            "is_weather": True, "weather_type": "temperature",
            "location_name": "Phoenix", "threshold_value": "90",
            "threshold_operator": "above", "threshold_unit": "fahrenheit",
            "parse_confidence": "medium",
            "ambiguity_flags": ["region_not_city"],
            "location_data": {"lat": 33.45, "lon": -112.07},
        }
        result = await engine.estimate_probability(parse)
        # Should still produce a result but with reduced confidence
        assert result.confidence_score < 0.8


class TestIntegration:
    """Parse → Probability → Score pipeline tests."""

    @pytest.mark.asyncio
    async def test_temperature_pipeline(self):
        """Full pipeline from question to scored signal."""
        from app.parsers.weather_parser import parse_weather_market
        from app.engines.signal_scorer import score_signal

        # 1. Parse
        parse = parse_weather_market("Will temperature exceed 90°F in Phoenix tomorrow?")
        assert parse["is_weather"]
        assert parse["weather_type"] == "temperature"

        # 2. Probability (mock)
        data = _make_forecast_data(temps_f=[95, 97, 93, 94, 96, 92, 95, 98])
        client = AsyncMock()
        client.get_forecast = AsyncMock(return_value=data)
        engine = WeatherProbabilityEngine(client=client)
        prob_result = await engine.estimate_probability(parse)

        assert prob_result.true_prob_raw > 0.5
        assert prob_result.confidence_score > 0.3

        # 3. Score
        signal = score_signal(
            market_yes_price=0.50,
            weather_result=prob_result,
            market_id=42,
        )

        assert signal["direction"] == "YES"
        assert signal["recommendation"] == "buy_yes"
        assert signal["edge"] > 0
        assert signal["explainability"]["weather_probability"] > 0.5

    @pytest.mark.asyncio
    async def test_rainfall_pipeline_rejection(self):
        """Pipeline that rejects due to no location."""
        from app.parsers.weather_parser import parse_weather_market
        from app.engines.signal_scorer import score_signal

        # 1. Parse (no location)
        parse = parse_weather_market("Will there be heavy rain tomorrow?")
        assert parse["is_weather"]
        assert parse["location_name"] is None

        # 2. Probability engine rejects
        engine = WeatherProbabilityEngine()
        prob_result = await engine.estimate_probability(parse)
        assert prob_result.source == "rejected"

        # 3. Score also rejects
        signal = score_signal(
            market_yes_price=0.50,
            weather_result=prob_result,
            market_id=99,
        )
        assert signal["recommendation"] == "skip"
        assert len(signal["rejection_reasons"]) > 0
