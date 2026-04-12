"""Tests for signal scoring engine."""

import pytest
from app.engines.signal_scorer import score_signal


class TestSignalScoring:
    def test_high_edge_buy_yes(self):
        """Weather says 80% but market says 50% → buy YES."""
        result = score_signal(market_yes_price=0.50, weather_prob=0.80, market_id=1)
        assert result["direction"] == "YES"
        assert result["recommendation"] == "buy_yes"
        assert result["edge"] == 0.30
        assert result["confidence"] == "high"

    def test_high_edge_buy_no(self):
        """Weather says 20% but market says 60% → buy NO."""
        result = score_signal(market_yes_price=0.60, weather_prob=0.20, market_id=1)
        assert result["direction"] == "NO"
        assert result["recommendation"] == "buy_no"
        assert result["edge"] == -0.40
        assert result["confidence"] == "high"

    def test_no_edge_skip(self):
        """Edge too small → skip."""
        result = score_signal(market_yes_price=0.50, weather_prob=0.52, market_id=1)
        assert result["direction"] is None
        assert result["recommendation"] == "skip"
        assert result["confidence"] == "none"

    def test_medium_confidence(self):
        result = score_signal(market_yes_price=0.50, weather_prob=0.62, market_id=1)
        assert result["confidence"] == "medium"
        assert result["direction"] == "YES"

    def test_low_confidence(self):
        result = score_signal(market_yes_price=0.50, weather_prob=0.57, market_id=1)
        assert result["confidence"] == "low"
        assert result["direction"] == "YES"

    def test_explainability(self):
        result = score_signal(market_yes_price=0.40, weather_prob=0.70, market_id=1)
        exp = result["explainability"]
        assert exp["market_price"] == 0.40
        assert exp["weather_probability"] == 0.70
        assert "edge" in exp
        assert exp["direction"] == "YES"
