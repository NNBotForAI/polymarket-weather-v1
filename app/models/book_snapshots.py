"""Book snapshots — order book / pricing data at a point in time."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class BookSnapshot(Base, TimestampMixin):
    __tablename__ = "book_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    market_id: Mapped[int] = mapped_column(BigInteger, index=True)
    yes_price: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    no_price: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    spread: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    volume_24h: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    raw_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    snapped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
