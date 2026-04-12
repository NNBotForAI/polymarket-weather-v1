"""Paper trades — simulated trades (no real money)."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class PaperTrade(Base, TimestampMixin):
    __tablename__ = "paper_trades"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    market_id: Mapped[int] = mapped_column(BigInteger, index=True)
    signal_id: Mapped[int] = mapped_column(BigInteger, index=True)
    direction: Mapped[str] = mapped_column(String(10))  # "YES" or "NO"
    entry_price: Mapped[float] = mapped_column(Numeric)
    quantity: Mapped[float] = mapped_column(Numeric, default=1.0)
    status: Mapped[str] = mapped_column(String(20), default="open", index=True)  # "open", "closed"
    exit_price: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    pnl: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
