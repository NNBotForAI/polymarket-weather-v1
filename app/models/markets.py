"""Markets — normalized market records."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Market(Base, TimestampMixin):
    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    polymarket_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    question: Mapped[str] = mapped_column(Text)
    slug: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outcomes: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    is_binary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_weather: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    closed: Mapped[bool] = mapped_column(Boolean, default=False)
    volume: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    liquidity: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    raw_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
