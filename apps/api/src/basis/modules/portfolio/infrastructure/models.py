"""SQLAlchemy persistence models for the portfolio context.

Note there is deliberately no foreign key to ``clients``: bounded contexts own
their data, and referential integrity across contexts is enforced by the
application layer, not by the database.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from basis.kernel.infrastructure.db import Base, TimestampMixin, UuidPrimaryKeyMixin

MONEY_PRECISION = 28
MONEY_SCALE = 10
QUANTITY_SCALE = 10


class PortfolioRow(Base, UuidPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "portfolios"

    client_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(5), nullable=False)
    status: Mapped[str] = mapped_column(String(20), index=True, nullable=False)


class PortfolioTargetRow(Base, UuidPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "portfolio_targets"

    portfolio_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    asset_class: Mapped[str] = mapped_column(String(20), nullable=False)
    weight_bps: Mapped[int] = mapped_column(Integer, nullable=False)


class PortfolioTransactionRow(Base, UuidPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "portfolio_transactions"
    __table_args__ = (
        Index("ix_portfolio_transactions_portfolio_id_trade_date", "portfolio_id", "trade_date"),
    )

    portfolio_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
    )
    instrument_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    symbol: Mapped[str] = mapped_column(String(15), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(20), nullable=False)
    currency: Mapped[str] = mapped_column(String(5), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(MONEY_PRECISION, QUANTITY_SCALE), nullable=False
    )
    price: Mapped[Decimal] = mapped_column(Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False)
    fees: Mapped[Decimal] = mapped_column(Numeric(MONEY_PRECISION, MONEY_SCALE), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(280))


__all__ = ["PortfolioRow", "PortfolioTargetRow", "PortfolioTransactionRow"]
