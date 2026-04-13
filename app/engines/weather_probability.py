"""Weather probability engine V1.1 — real probability estimation.

Supported types: temperature thresholds, rainfall thresholds, hurricane/wind.
Uses OpenWeatherMap forecast data with statistical methods.
Falls back conservatively when data is unavailable.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.clients.weather import WeatherClient, get_weather_client
from app.parsers.weather_parser import SUPPORTED_WEATHER_TYPES

logger = logging.getLogger(__name__)

# Maximum data age in minutes before confidence degrades
FRESHNESS_THRESHOLD_MINUTES = 180  # 3 hours

# Confidence multiplier when data is stale
STALE_CONFIDENCE_MULTIPLIER = 0.5

# Minimum number of forecast data points for statistical reliability
MIN_FORECAST_POINTS = 4


class WeatherProbabilityResult:
    """Structured output from the probability engine."""

    def __init__(
        self,
        true_prob_raw: float,
        confidence_score: float,  # 0.0 - 1.0
        data_freshness_minutes: float | None,
        model_notes: str,
        feature_json: dict[str, Any],
        source: str,
        weather_type: str | None,
    ):
        self.true_prob_raw = true_prob_raw
        self.confidence_score = confidence_score
        self.data_freshness_minutes = data_freshness_minutes
        self.model_notes = model_notes
        self.feature_json = feature_json
        self.source = source
        self.weather_type = weather_type

    def to_dict(self) -> dict[str, Any]:
        return {
            "true_prob_raw": self.true_prob_raw,
            "confidence_score": self.confidence_score,
            "data_freshness_minutes": self.data_freshness_minutes,
            "model_notes": self.model_notes,
            "feature_json": self.feature_json,
            "source": self.source,
            "weather_type": self.weather_type,
        }


class WeatherProbabilityEngine:
    """V1.1 weather probability engine.

    For each supported weather type:
    - Fetches forecast data from OpenWeatherMap
    - Applies statistical methods to estimate P(threshold is met)
    - Returns structured result with explainability
    """

    def __init__(self, client: WeatherClient | None = None):
        self._client = client

    async def _get_client(self) -> WeatherClient:
        if self._client is None:
            self._client = get_weather_client()
        return self._client

    async def estimate_probability(self, parse_result: dict[str, Any]) -> WeatherProbabilityResult:
        """Estimate P(event) from a parsed weather market.

        Args:
            parse_result: Output from weather_parser.parse_weather_market()

        Returns:
            WeatherProbabilityResult with probability, confidence, and explainability.
        """
        weather_type = parse_result.get("weather_type")
        location_name = parse_result.get("location_name")
        threshold_value = parse_result.get("threshold_value")
        threshold_operator = parse_result.get("threshold_operator")
        threshold_unit = parse_result.get("threshold_unit")
        location_data = parse_result.get("location_data")
        parse_confidence = parse_result.get("parse_confidence", "none")

        # ── Pre-checks ──
        if not parse_result.get("is_weather"):
            return self._reject("not_a_weather_market", weather_type, parse_result)

        if weather_type not in SUPPORTED_WEATHER_TYPES:
            return self._reject(f"unsupported_weather_type:{weather_type}", weather_type, parse_result)

        if not location_name:
            return self._reject("missing_location", weather_type, parse_result)

        if not threshold_value:
            return self._reject("missing_threshold", weather_type, parse_result)

        if parse_confidence == "low":
            return self._reject("parser_confidence_too_low", weather_type, parse_result)

        # ── Fetch weather data ──
        client = await self._get_client()
        lat = location_data.get("lat") if location_data else None
        lon = location_data.get("lon") if location_data else None
        forecast_data = await client.get_forecast(location_name, lat=lat, lon=lon)

        if forecast_data is None or not forecast_data.forecasts:
            return self._reject("insufficient_weather_data", weather_type, parse_result)

        # ── Calculate freshness ──
        data_freshness_minutes = self._calc_freshness(forecast_data.fetched_at)

        # ── Dispatch to type-specific estimator ──
        try:
            threshold_num = float(threshold_value)
        except (ValueError, TypeError):
            return self._reject("invalid_threshold_value", weather_type, parse_result)

        if weather_type == "temperature":
            result = await self._estimate_temperature(
                forecast_data, threshold_num, threshold_operator, threshold_unit, parse_result
            )
        elif weather_type == "rainfall":
            result = await self._estimate_rainfall(
                forecast_data, threshold_num, threshold_operator, threshold_unit, parse_result
            )
        elif weather_type == "hurricane":
            result = await self._estimate_hurricane(
                forecast_data, threshold_num, threshold_operator, threshold_unit, parse_result
            )
        else:
            return self._reject(f"unsupported:{weather_type}", weather_type, parse_result)

        # ── Apply freshness penalty ──
        if data_freshness_minutes and data_freshness_minutes > FRESHNESS_THRESHOLD_MINUTES:
            result.confidence_score *= STALE_CONFIDENCE_MULTIPLIER
            result.model_notes += f" [STALE DATA: {data_freshness_minutes:.0f}min old, confidence halved]"

        # ── Apply parse confidence penalty ──
        if parse_confidence == "medium":
            result.confidence_score *= 0.8
            result.model_notes += " [parse_confidence=medium, confidence reduced 20%]"

        # Clamp
        result.true_prob_raw = max(0.0, min(1.0, result.true_prob_raw))
        result.confidence_score = max(0.0, min(1.0, result.confidence_score))

        return result

    async def _estimate_temperature(
        self,
        forecast_data: Any,
        threshold: float,
        operator: str | None,
        unit: str | None,
        parse_result: dict[str, Any],
    ) -> WeatherProbabilityResult:
        """Estimate P(temperature meets threshold).

        Method: Extract forecasted temps, count how many exceed the threshold,
        then use hit ratio as base probability with Gaussian smoothing.
        """
        temps = []
        for f in forecast_data.forecasts:
            if f.get("temp_f") is not None:
                temps.append(f["temp_f"])

        if len(temps) < MIN_FORECAST_POINTS:
            return self._reject("insufficient_forecast_points", "temperature", parse_result,
                                feature_json={"temps_available": len(temps)})

        # Normalize threshold to Fahrenheit if needed
        threshold_f = self._to_fahrenheit(threshold, unit)

        # Count hits based on operator
        if operator in ("above", "at_least", "reach"):
            hits = sum(1 for t in temps if t >= threshold_f)
        elif operator in ("below", "at_most"):
            hits = sum(1 for t in temps if t <= threshold_f)
        elif operator == "exactly":
            hits = sum(1 for t in temps if abs(t - threshold_f) < 1.0)
        else:
            # Default: assume "above" for temperature
            hits = sum(1 for t in temps if t >= threshold_f)

        raw_prob = hits / len(temps)

        # Compute stats for explainability
        avg_temp = sum(temps) / len(temps)
        min_temp = min(temps)
        max_temp = max(temps)
        std_temp = (sum((t - avg_temp) ** 2 for t in temps) / len(temps)) ** 0.5

        # Confidence based on proximity of avg to threshold and spread
        # If threshold is far from average, higher confidence in direction
        z_score = abs(avg_temp - threshold_f) / max(std_temp, 0.1)
        confidence = min(0.95, 0.4 + z_score * 0.1)

        feature_json = {
            "method": "forecast_hit_ratio",
            "forecast_count": len(temps),
            "hits": hits,
            "raw_hit_ratio": round(raw_prob, 4),
            "threshold_f": threshold_f,
            "operator": operator or "above",
            "avg_temp_f": round(avg_temp, 2),
            "min_temp_f": round(min_temp, 2),
            "max_temp_f": round(max_temp, 2),
            "std_temp_f": round(std_temp, 2),
            "z_score": round(z_score, 2),
            "location": forecast_data.location_name,
        }

        return WeatherProbabilityResult(
            true_prob_raw=round(raw_prob, 4),
            confidence_score=round(confidence, 4),
            data_freshness_minutes=self._calc_freshness(forecast_data.fetched_at),
            model_notes=f"Temperature: {hits}/{len(temps)} forecast points meet threshold {threshold_f}°F ({operator})",
            feature_json=feature_json,
            source="openweathermap_forecast",
            weather_type="temperature",
        )

    async def _estimate_rainfall(
        self,
        forecast_data: Any,
        threshold: float,
        operator: str | None,
        unit: str | None,
        parse_result: dict[str, Any],
    ) -> WeatherProbabilityResult:
        """Estimate P(rainfall meets threshold).

        Method: Use OWM's pop (probability of precipitation) field as base,
        then adjust based on forecasted rainfall amounts vs threshold.
        """
        # Convert threshold to inches if needed
        threshold_in = self._to_inches(threshold, unit)

        total_rain = 0.0
        pop_values: list[float] = []
        rainy_periods = 0

        for f in forecast_data.forecasts:
            rain_3h = f.get("rain_3h_in") or 0.0
            pop = f.get("pop") or 0.0
            total_rain += rain_3h
            pop_values.append(pop)
            if rain_3h > 0:
                rainy_periods += 1

        if not pop_values:
            return self._reject("no_precipitation_data", "rainfall", parse_result)

        avg_pop = sum(pop_values) / len(pop_values)

        # Base probability: weighted combination of POP and actual forecast amounts
        if operator in ("above", "at_least", "reach") or operator is None:
            # P(total rain >= threshold)
            # Use ratio of forecasted total to threshold as a simple estimator
            if threshold_in <= 0:
                raw_prob = avg_pop
            else:
                # If forecasted total exceeds threshold, high probability
                amount_ratio = min(total_rain / threshold_in, 2.0) if threshold_in > 0 else 2.0
                # Blend POP with amount ratio
                raw_prob = 0.5 * avg_pop + 0.5 * min(amount_ratio, 1.0)
        elif operator in ("below", "at_most"):
            raw_prob = 1.0 - (0.5 * avg_pop + 0.5 * min(total_rain / max(threshold_in, 0.01), 1.0))
        else:
            raw_prob = avg_pop

        # Confidence: higher with more data points, lower with sparse rain data
        confidence = min(0.85, 0.3 + len(pop_values) * 0.03)
        if rainy_periods == 0 and threshold_in > 0:
            confidence *= 0.7  # No rain forecasted but threshold > 0 → less certain

        feature_json = {
            "method": "pop_plus_amount_ratio",
            "forecast_count": len(pop_values),
            "avg_pop": round(avg_pop, 4),
            "total_rain_in": round(total_rain, 4),
            "threshold_in": round(threshold_in, 4),
            "rainy_periods": rainy_periods,
            "operator": operator or "above",
            "location": forecast_data.location_name,
        }

        return WeatherProbabilityResult(
            true_prob_raw=round(raw_prob, 4),
            confidence_score=round(confidence, 4),
            data_freshness_minutes=self._calc_freshness(forecast_data.fetched_at),
            model_notes=f"Rainfall: avg POP={avg_pop:.0%}, total forecasted={total_rain:.2f}in vs threshold={threshold_in:.2f}in",
            feature_json=feature_json,
            source="openweathermap_forecast",
            weather_type="rainfall",
        )

    async def _estimate_hurricane(
        self,
        forecast_data: Any,
        threshold: float,
        operator: str | None,
        unit: str | None,
        parse_result: dict[str, Any],
    ) -> WeatherProbabilityResult:
        """Estimate P(wind speed meets hurricane threshold).

        Method: Use forecasted wind speeds, count exceedances.
        Note: OWM doesn't provide hurricane-specific data. This uses
        surface wind speeds as a proxy, which significantly underestimates
        hurricane conditions. Mark as LOW_CONFIDENCE.
        """
        wind_speeds: list[float] = []
        wind_gusts: list[float] = []

        for f in forecast_data.forecasts:
            ws = f.get("wind_speed_mph")
            wg = f.get("wind_gust_mph")
            if ws is not None:
                wind_speeds.append(ws)
            if wg is not None:
                wind_gusts.append(wg)

        if not wind_speeds:
            return self._reject("no_wind_data", "hurricane", parse_result)

        # Use gusts if available (higher = more relevant for hurricane)
        all_wind = wind_gusts if wind_gusts else wind_speeds

        # Default threshold: Category 1 hurricane = 74 mph
        if operator in ("above", "at_least", "reach") or operator is None:
            hits = sum(1 for w in all_wind if w >= threshold)
        elif operator in ("below", "at_most"):
            hits = sum(1 for w in all_wind if w <= threshold)
        else:
            hits = sum(1 for w in all_wind if w >= threshold)

        raw_prob = hits / len(all_wind) if all_wind else 0.0

        # IMPORTANT: Low confidence because OWM surface winds ≠ hurricane winds
        # Real hurricane probability requires specialized data (NHC, etc.)
        confidence = min(0.4, raw_prob * 0.5)  # Cap at 0.4

        feature_json = {
            "method": "wind_speed_exceedance",
            "forecast_count": len(all_wind),
            "hits": hits,
            "threshold_mph": threshold,
            "operator": operator or "above",
            "avg_wind_mph": round(sum(wind_speeds) / max(len(wind_speeds), 1), 2),
            "max_wind_mph": round(max(wind_speeds), 2) if wind_speeds else None,
            "max_gust_mph": round(max(wind_gusts), 2) if wind_gusts else None,
            "limitation": "OWM provides surface winds, not hurricane-level data. Use NHC for real hurricane probability.",
            "location": forecast_data.location_name,
        }

        return WeatherProbabilityResult(
            true_prob_raw=round(raw_prob, 4),
            confidence_score=round(confidence, 4),
            data_freshness_minutes=self._calc_freshness(forecast_data.fetched_at),
            model_notes=f"Hurricane/Wind: {hits}/{len(all_wind)} exceed {threshold}mph. LIMITATION: surface winds only, not hurricane-specific data.",
            feature_json=feature_json,
            source="openweathermap_forecast",
            weather_type="hurricane",
        )

    # ── Helpers ──────────────────────────────────────────────────────

    def _reject(
        self,
        reason: str,
        weather_type: str | None,
        parse_result: dict[str, Any],
        feature_json: dict[str, Any] | None = None,
    ) -> WeatherProbabilityResult:
        """Return a rejected/low-confidence result."""
        return WeatherProbabilityResult(
            true_prob_raw=0.5,
            confidence_score=0.0,
            data_freshness_minutes=None,
            model_notes=f"REJECTED: {reason}",
            feature_json={
                "rejection_reason": reason,
                "weather_type": weather_type,
                "parse_result": {
                    "location_name": parse_result.get("location_name"),
                    "threshold_value": parse_result.get("threshold_value"),
                    "weather_type": parse_result.get("weather_type"),
                },
                **(feature_json or {}),
            },
            source="rejected",
            weather_type=weather_type,
        )

    @staticmethod
    def _calc_freshness(fetched_at: datetime) -> float | None:
        """Calculate minutes since data was fetched."""
        if fetched_at is None:
            return None
        delta = datetime.now(timezone.utc) - fetched_at
        return max(0.0, delta.total_seconds() / 60.0)

    @staticmethod
    def _to_fahrenheit(value: float, unit: str | None) -> float:
        """Convert a temperature value to Fahrenheit."""
        if unit in ("celsius", "°c", "c"):
            return value * 9 / 5 + 32
        return value  # Assume Fahrenheit if unknown

    @staticmethod
    def _to_inches(value: float, unit: str | None) -> float:
        """Convert a rainfall value to inches."""
        if unit in ("mm",):
            return value / 25.4
        if unit in ("cm",):
            return value / 2.54
        return value  # Assume inches if unknown


def get_weather_engine(client: WeatherClient | None = None) -> WeatherProbabilityEngine:
    """Factory to get the weather probability engine."""
    return WeatherProbabilityEngine(client=client)
