"""End-to-end sample test demonstrating parse → probability → score pipeline."""

from __future__ import annotations
from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock

from app.clients.weather import WeatherData
from app.parsers.weather_parser import parse_weather_market
from app.engines.weather_probability import WeatherProbabilityEngine
from app.engines.signal_scorer import score_signal


def _make_mock_forecast(location: str, temps_f: list[float] | None = None):
    """Create mock forecast data compatible with WeatherData."""
    from app.clients.weather import WeatherData
    base_timestamp = int(datetime.now(timezone.utc).timestamp())
    forecasts = [
        {
            "dt": base_timestamp + i * 10800,
            "dt_txt": "test",
            "temp_f": t,
            "temp_min_f": t - 2,
            "temp_max_f": t + 2,
            "humidity_pct": 50,
            "wind_speed_mph": 10,
            "pop": 1.0,
        }
        for i, t in enumerate(temps_f or [90, 92, 95, 88, 91, 93, 96, 97, 98, 95, 99, 100])
    ]

    # Create WeatherData-like object
    data = WeatherData(
        source="mock",
        location_name=location,
        lat=40.71,
        lon=-74.01,
        fetched_at=datetime.now(timezone.utc),
        current={"temp_f": 85.0},
        forecasts=forecasts,
        raw={},
    )
    return data


class TestEndToEndSample:
    """Sample end-to-end pipeline tests."""

    @pytest.mark.asyncio
    async def test_temperature_buy_signal(self):
        """Full pipeline: parse → probability → score (temperature, high edge)."""
        # 1. Parse market question
        parse = parse_weather_market("Will temperature exceed 90°F in Phoenix tomorrow?")
        assert parse["is_weather"] is True
        assert parse["weather_type"] == "temperature"
        assert parse["location_name"] == "Phoenix"
        assert parse["threshold_value"] == "90"
        assert parse["threshold_unit"] == "fahrenheit"
        assert parse["parse_confidence"] in ("high", "medium")

        # 2. Get weather probability (mocked)
        mock_client = AsyncMock()
        mock_client.get_forecast = AsyncMock(
            return_value=_make_mock_forecast("Phoenix", temps_f=[92, 94, 96, 95, 93, 97, 98, 95, 99, 100])
        )
        engine = WeatherProbabilityEngine(client=mock_client)
        prob_result = await engine.estimate_probability(parse)

        # 3. Verify probability
        assert prob_result.source == "openweathermap_forecast"
        assert prob_result.weather_type == "temperature"
        assert prob_result.true_prob_raw > 0.8  # Most temps above 90°F
        assert prob_result.confidence_score > 0.5

        # 4. Score signal
        signal = score_signal(
            market_yes_price=0.50,
            weather_result=prob_result,
            market_id=42,
        )

        # 5. Verify signal
        assert signal["direction"] == "YES"
        assert signal["recommendation"] == "buy_yes"
        assert signal["confidence"] in ("high", "medium")
        assert signal["edge"] > 0.15
        assert len(signal["rejection_reasons"]) == 0
        assert signal["explainability"]["weather_probability"] == prob_result.true_prob_raw

        # Print sample output
        print(f"\n=== Sample Output: Temperature Buy YES ===")
        print(f"Market: Will temperature exceed 90°F in Phoenix tomorrow?")
        print(f"Price: 50¢ (YES)")
        print(f"Probability: {prob_result.true_prob_raw:.2%} ({prob_result.confidence_score:.2f} confidence)")
        print(f"Signal: BUY YES (edge: {signal['edge']:+.1%})")

    @pytest.mark.asyncio
    async def test_temperature_skip_signal(self):
        """Full pipeline with edge too small."""
        # 1. Parse
        parse = parse_weather_market("Will temperature exceed 100°F in Phoenix?")
        assert parse["is_weather"] is True

        # 2. Probability (mocked)
        mock_client = AsyncMock()
        mock_client.get_forecast = AsyncMock(
            return_value=_make_mock_forecast("Phoenix", temps_f=[95, 96, 95, 94, 97, 96, 98, 99])
        )
        engine = WeatherProbabilityEngine(client=mock_client)
        prob_result = await engine.estimate_probability(parse)

        # 3. Score
        signal = score_signal(market_yes_price=0.48, weather_result=prob_result, market_id=43)

        # 4. Verify skip
        assert signal["recommendation"] == "skip"
        assert "edge_too_small" in signal["rejection_reasons"]

        print(f"\n=== Sample Output: Temperature Skip ===")
        print(f"Market: Will temperature exceed 100°F in Phoenix?")
        print(f"Price: 48¢ (YES)")
        print(f"Probability: {prob_result.true_prob_raw:.2%}")
        print(f"Signal: SKIP (edge too small: {abs(prob_result.true_prob_raw - 0.48):.2%})")

    @pytest.mark.asyncio
    async def test_rainfall_rejected(self):
        """Full pipeline rejected due to missing location."""
        # 1. Parse
        parse = parse_weather_market("Will there be heavy rain tomorrow?")
        assert parse["is_weather"] is True
        assert parse["weather_type"] == "rainfall"
        assert parse["location_name"] is None  # Missing location!

        # 2. Probability engine should reject
        mock_client = AsyncMock()
        mock_client.get_forecast = AsyncMock(return_value=None)
        engine = WeatherProbabilityEngine(client=mock_client)
        prob_result = await engine.estimate_probability(parse)

        # 3. Score should also reject
        signal = score_signal(market_yes_price=0.50, weather_result=prob_result, market_id=44)

        assert prob_result.source == "rejected"
        assert "missing_location" in signal["rejection_reasons"]
        assert signal["recommendation"] == "skip"

        print(f"\n=== Sample Output: Rainfall Rejected ===")
        print(f"Market: Will there be heavy rain tomorrow?")
        print(f"Reason: Missing location")
        print(f"Signal: SKIP")
