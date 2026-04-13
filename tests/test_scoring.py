"""Tests for signal scoring engine V1.1."""

import pytest
from app.engines.signal_scorer import score_signal, score_signal_simple
from app.engines.weather_probability import WeatherProbabilityResult


def _make_weather_result(
    prob: float = 0.8,
    confidence: float = 0.7,
    freshness: float = 10.0,
    source: str = "openweathermap_forecast",
    weather_type: str = "temperature",
    notes: str = "test",
) -> WeatherProbabilityResult:
    return WeatherProbabilityResult(
        true_prob_raw=prob,
        confidence_score=confidence,
        data_freshness_minutes=freshness,
        model_notes=notes,
        feature_json={"method": "test"},
        source=source,
        weather_type=weather_type,
    )


class TestSignalScoringV11:
    def test_high_edge_buy_yes(self):
        wr = _make_weather_result(prob=0.80, confidence=0.8)
        result = score_signal(market_yes_price=0.50, weather_result=wr, market_id=1)
        assert result["direction"] == "YES"
        assert result["recommendation"] == "buy_yes"
        assert result["edge"] > 0
        assert result["confidence"] == "high"

    def test_high_edge_buy_no(self):
        wr = _make_weather_result(prob=0.20, confidence=0.8)
        result = score_signal(market_yes_price=0.60, weather_result=wr, market_id=1)
        assert result["direction"] == "NO"
        assert result["recommendation"] == "buy_no"
        assert result["confidence"] == "high"

    def test_no_edge_skip(self):
        wr = _make_weather_result(prob=0.52, confidence=0.8)
        result = score_signal(market_yes_price=0.50, weather_result=wr, market_id=1)
        assert result["direction"] is None
        assert result["recommendation"] == "skip"
        assert "edge_too_small" in result["rejection_reasons"]

    def test_stale_data_rejected(self):
        wr = _make_weather_result(prob=0.80, confidence=0.7, freshness=400.0)
        result = score_signal(market_yes_price=0.50, weather_result=wr, market_id=1)
        assert "stale_weather_data" in result["rejection_reasons"]
        assert result["recommendation"] == "skip"

    def test_spread_too_wide(self):
        wr = _make_weather_result(prob=0.80, confidence=0.8)
        result = score_signal(market_yes_price=0.50, weather_result=wr, market_id=1, spread=0.15)
        assert "spread_too_wide" in result["rejection_reasons"]

    def test_low_weather_confidence_rejected(self):
        wr = _make_weather_result(prob=0.80, confidence=0.1)
        result = score_signal(market_yes_price=0.50, weather_result=wr, market_id=1)
        assert "insufficient_weather_confidence" in result["rejection_reasons"]

    def test_parser_confidence_low_rejected(self):
        wr = _make_weather_result(prob=0.80, confidence=0.7)
        result = score_signal(
            market_yes_price=0.50, weather_result=wr, market_id=1,
            parse_confidence="low"
        )
        assert "parser_confidence_too_low" in result["rejection_reasons"]

    def test_rejected_weather_engine(self):
        wr = _make_weather_result(source="rejected", notes="REJECTED: missing_location")
        result = score_signal(market_yes_price=0.50, weather_result=wr, market_id=1)
        assert result["recommendation"] == "skip"

    def test_explainability_has_all_fields(self):
        wr = _make_weather_result(prob=0.70, confidence=0.6)
        result = score_signal(market_yes_price=0.40, weather_result=wr, market_id=1)
        exp = result["explainability"]
        assert "weather_confidence" in exp
        assert "data_freshness_minutes" in exp
        assert "weather_source" in exp
        assert "feature_json" in exp
        assert "rejection_reasons" in exp

    def test_medium_confidence_signal(self):
        wr = _make_weather_result(prob=0.65, confidence=0.8)
        result = score_signal(market_yes_price=0.50, weather_result=wr, market_id=1)
        assert result["confidence"] in ("medium", "high")  # 0.15 edge = high threshold
        assert result["direction"] == "YES"

    def test_low_weather_confidence_downgrades_signal(self):
        wr = _make_weather_result(prob=0.80, confidence=0.5)
        result = score_signal(market_yes_price=0.50, weather_result=wr, market_id=1)
        assert result["confidence"] == "low"  # downgraded from high edge due to low weather confidence


class TestScoreSignalSimple:
    """Backward-compat wrapper tests."""

    def test_simple_high_edge(self):
        result = score_signal_simple(market_yes_price=0.50, weather_prob=0.80, market_id=1)
        assert result["direction"] == "YES"

    def test_simple_no_edge(self):
        result = score_signal_simple(market_yes_price=0.50, weather_prob=0.52, market_id=1)
        assert result["recommendation"] == "skip"
