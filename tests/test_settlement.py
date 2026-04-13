"""Tests for paper trade settlement and safety thresholds."""

import pytest
from app.engines.paper_trader import should_open_trade, create_trade_params, settle_trade


class TestShouldOpenTradeV11:
    def test_open_valid_trade(self):
        signal = {
            "market_id": 1, "recommendation": "buy_yes", "direction": "YES",
            "edge": 0.2, "confidence": "high",
            "explainability": {"weather_confidence": 0.8},
            "rejection_reasons": [],
        }
        should, reason = should_open_trade(signal, [])
        assert should is True

    def test_skip_no_edge(self):
        signal = {
            "market_id": 1, "recommendation": "skip", "direction": None,
            "edge": 0.01, "confidence": "none",
            "explainability": {"weather_confidence": 0.5},
            "rejection_reasons": ["edge_too_small"],
        }
        should, reason = should_open_trade(signal, [])
        assert should is False
        assert "skip" in reason.lower()

    def test_skip_existing_open(self):
        signal = {
            "market_id": 1, "recommendation": "buy_yes", "direction": "YES",
            "edge": 0.2, "confidence": "high",
            "explainability": {"weather_confidence": 0.8},
            "rejection_reasons": [],
        }
        existing = [{"id": 10, "market_id": 1, "status": "open"}]
        should, reason = should_open_trade(signal, existing)
        assert should is False
        assert "already" in reason.lower()

    def test_skip_low_weather_confidence(self):
        signal = {
            "market_id": 1, "recommendation": "buy_yes", "direction": "YES",
            "edge": 0.2, "confidence": "high",
            "explainability": {"weather_confidence": 0.1},
            "rejection_reasons": [],
        }
        should, reason = should_open_trade(signal, [])
        assert should is False
        assert "weather_confidence" in reason.lower()

    def test_skip_has_rejection_reasons(self):
        signal = {
            "market_id": 1, "recommendation": "buy_yes", "direction": "YES",
            "edge": 0.2, "confidence": "high",
            "explainability": {"weather_confidence": 0.8},
            "rejection_reasons": ["stale_weather_data"],
        }
        should, reason = should_open_trade(signal, [])
        assert should is False
        assert "rejection" in reason.lower()

    def test_skip_ambiguous_market(self):
        signal = {
            "market_id": 1, "recommendation": "buy_yes", "direction": "YES",
            "edge": 0.2, "confidence": "medium",
            "explainability": {
                "weather_confidence": 0.8,
                "feature_json": {"rejection_reason": "ambiguous_market"},
            },
            "rejection_reasons": [],
        }
        should, reason = should_open_trade(signal, [])
        assert should is False
        assert "ambiguous" in reason.lower()


class TestCreateTradeParams:
    def test_buy_yes(self):
        signal = {
            "market_id": 1, "id": 5, "direction": "YES",
            "market_yes_price": 0.60, "edge": 0.15, "confidence": "high",
            "explainability": {"weather_confidence": 0.8},
        }
        params = create_trade_params(signal)
        assert params["direction"] == "YES"
        assert params["entry_price"] == 0.60
        assert params["quantity"] == 1.0
        assert params["status"] == "open"

    def test_buy_no(self):
        signal = {
            "market_id": 2, "id": 6, "direction": "NO",
            "market_yes_price": 0.70, "edge": -0.20, "confidence": "high",
            "explainability": {"weather_confidence": 0.8},
        }
        params = create_trade_params(signal)
        assert params["direction"] == "NO"
        assert params["entry_price"] == 0.30


class TestSettleTrade:
    def test_win_yes(self):
        trade = {"direction": "YES", "entry_price": 0.60, "quantity": 1.0, "notes": ""}
        result = settle_trade(trade, "Yes")
        assert result["exit_price"] == 1.0
        assert result["pnl"] == 0.40
        assert result["status"] == "closed"

    def test_lose_yes(self):
        trade = {"direction": "YES", "entry_price": 0.60, "quantity": 1.0, "notes": ""}
        result = settle_trade(trade, "No")
        assert result["exit_price"] == 0.0
        assert result["pnl"] == -0.60

    def test_win_no(self):
        trade = {"direction": "NO", "entry_price": 0.30, "quantity": 1.0, "notes": ""}
        result = settle_trade(trade, "No")
        assert result["pnl"] == 0.70

    def test_lose_no(self):
        trade = {"direction": "NO", "entry_price": 0.30, "quantity": 1.0, "notes": ""}
        result = settle_trade(trade, "Yes")
        assert result["pnl"] == -0.30
