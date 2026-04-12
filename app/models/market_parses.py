"""Market parses — parsed/extracted structured data from market questions."""

from typing import Any, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MarketParse(Base, TimestampMixin):
    __tablename__ = "market_parses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    market_id: Mapped[int] = mapped_column(BigInteger, index=True)
    is_weather: Mapped[bool] = mapped_column(Boolean, default=False)
    is_binary: Mapped[bool] = mapped_column(Boolean, default=False)
    is_ambiguous: Mapped[bool] = mapped_column(Boolean, default=False)
    ambiguity_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    metric: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # temperature, rainfall, etc.
    threshold: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    comparator: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # above, below, exactly
    target_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    parse_meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
