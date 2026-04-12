"""Signal scores — comparison of market price vs weather probability."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SignalScore(Base, TimestampMixin):
    __tablename__ = "signal_scores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    market_id: Mapped[int] = mapped_column(BigInteger, index=True)
    book_snapshot_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    weather_model_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    market_yes_price: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    weather_prob: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    edge: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)  # weather_prob - market_price
    direction: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # "YES" or "NO"
    confidence: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # "high", "medium", "low"
    recommendation: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # "buy_yes", "buy_no", "skip"
    explainability: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    scored_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
