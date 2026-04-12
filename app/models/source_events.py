"""Source events — raw data from Polymarket API."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SourceEvent(Base, TimestampMixin):
    __tablename__ = "source_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), index=True)  # "polymarket_gamma"
    event_type: Mapped[str] = mapped_column(String(100))  # "market_discovery"
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
