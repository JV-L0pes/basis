"""Read models (DTOs) for the portfolio context."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from basis.kernel.domain.money import Money
from basis.modules.portfolio.domain.models import Portfolio, Transaction
from basis.modules.portfolio.domain.valuation import PortfolioValuation


@dataclass(frozen=True, slots=True)
class TargetWeightView:
    asset_class: str
    weight_bps: int
    weight_percent: Decimal


@dataclass(frozen=True, slots=True)
class TransactionView:
    id: UUID
    symbol: str
    asset_class: str
    kind: str
    trade_date: date
    quantity: Decimal
    price: Money
    fees: Money
    gross_value: Money
    notes: str | None

    @classmethod
    def from_entity(cls, transaction: Transaction) -> TransactionView:
        return cls(
            id=transaction.id,
            symbol=transaction.instrument.symbol,
            asset_class=str(transaction.instrument.asset_class),
            kind=str(transaction.kind),
            trade_date=transaction.trade_date,
            quantity=transaction.quantity,
            price=transaction.price,
            fees=transaction.fees,
            gross_value=transaction.gross_value,
            notes=transaction.notes,
        )


@dataclass(frozen=True, slots=True)
class PortfolioView:
    id: UUID
    client_id: UUID
    name: str
    base_currency: str
    status: str
    targets: tuple[TargetWeightView, ...]
    position_count: int
    transaction_count: int
    created_at: datetime
    updated_at: datetime
    valuation: PortfolioValuation | None = None

    @classmethod
    def from_entity(
        cls, portfolio: Portfolio, *, valuation: PortfolioValuation | None = None
    ) -> PortfolioView:
        return cls(
            id=portfolio.id,
            client_id=portfolio.client_id,
            name=portfolio.name,
            base_currency=portfolio.base_currency.code,
            status=str(portfolio.status),
            targets=tuple(
                TargetWeightView(
                    asset_class=str(target.asset_class),
                    weight_bps=target.weight_bps,
                    weight_percent=target.percent,
                )
                for target in portfolio.targets
            ),
            position_count=len(portfolio.positions()),
            transaction_count=portfolio.transaction_count(),
            created_at=portfolio.created_at,
            updated_at=portfolio.updated_at,
            valuation=valuation,
        )


@dataclass(frozen=True, slots=True)
class PortfolioPage:
    items: list[PortfolioView]
    next_cursor: str | None = None

    @property
    def has_more(self) -> bool:
        return self.next_cursor is not None


__all__ = ["PortfolioPage", "PortfolioView", "TargetWeightView", "TransactionView"]
