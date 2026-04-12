"""Market resolutions — actual outcomes for settled markets."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import BigInteger, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class MarketResolution(Base, TimestampMixin):
    __tablename__ = "market_resolutions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    market_id: Mapped[int] = mapped_column(BigInteger, index=True)
    outcome: Mapped[str] = mapped_column(String(10))  # "Yes", "No"
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
