"""Weather model runs — external weather probability estimates."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class WeatherModelRun(Base, TimestampMixin):
    __tablename__ = "weather_model_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    market_id: Mapped[int] = mapped_column(BigInteger, index=True)
    source: Mapped[str] = mapped_column(String(100))  # "openweathermap", "noaa", etc.
    probability_yes: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    model_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    forecast_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
