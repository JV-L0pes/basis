"""SQLAlchemy persistence models for the market data context."""

from __future__ import annotations

from sqlalchemy import Boolean, String, text
from sqlalchemy.orm import Mapped, mapped_column

from basis.kernel.infrastructure.db import Base, TimestampMixin, UuidPrimaryKeyMixin


class InstrumentRow(Base, UuidPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "instruments"

    symbol: Mapped[str] = mapped_column(String(15), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(5), nullable=False)
    mic: Mapped[str | None] = mapped_column(String(8))
    isin: Mapped[str | None] = mapped_column(String(12), unique=True, index=True)
    cfi: Mapped[str | None] = mapped_column(String(6))
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )


__all__ = ["InstrumentRow"]
