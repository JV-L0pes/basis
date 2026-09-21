"""Mapping between persistence rows and domain objects (portfolio context)."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from basis.kernel.domain.assets import AssetClass
from basis.kernel.domain.currency import Currency
from basis.kernel.domain.money import Money
from basis.modules.portfolio.domain.models import Portfolio, Transaction
from basis.modules.portfolio.domain.value_objects import (
    AllocationTargets,
    InstrumentRef,
    PortfolioStatus,
    TargetAllocation,
    TransactionKind,
)
from basis.modules.portfolio.infrastructure.models import (
    PortfolioRow,
    PortfolioTargetRow,
    PortfolioTransactionRow,
)


def portfolio_to_domain(
    row: PortfolioRow,
    targets: Sequence[PortfolioTargetRow],
    transactions: Sequence[PortfolioTransactionRow],
) -> Portfolio:
    return Portfolio(
        id=row.id,
        client_id=row.client_id,
        name=row.name,
        base_currency=Currency.of(row.base_currency),
        status=PortfolioStatus(row.status),
        targets=AllocationTargets(
            [
                TargetAllocation(
                    asset_class=AssetClass(target.asset_class), weight_bps=target.weight_bps
                )
                for target in targets
            ]
        ),
        transactions=tuple(transaction_to_domain(item) for item in transactions),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def portfolio_to_row(portfolio: Portfolio) -> PortfolioRow:
    return PortfolioRow(
        id=portfolio.id,
        client_id=portfolio.client_id,
        name=portfolio.name,
        base_currency=portfolio.base_currency.code,
        status=str(portfolio.status),
        created_at=portfolio.created_at,
        updated_at=portfolio.updated_at,
    )


def apply_portfolio(portfolio: Portfolio, row: PortfolioRow) -> None:
    row.name = portfolio.name
    row.base_currency = portfolio.base_currency.code
    row.status = str(portfolio.status)
    row.updated_at = portfolio.updated_at


def target_to_row(target: TargetAllocation, portfolio_id: UUID) -> PortfolioTargetRow:
    return PortfolioTargetRow(
        portfolio_id=portfolio_id,
        asset_class=str(target.asset_class),
        weight_bps=target.weight_bps,
    )


def transaction_to_row(transaction: Transaction, portfolio_id: UUID) -> PortfolioTransactionRow:
    return PortfolioTransactionRow(
        id=transaction.id,
        portfolio_id=portfolio_id,
        instrument_id=transaction.instrument.instrument_id,
        symbol=transaction.instrument.symbol,
        asset_class=str(transaction.instrument.asset_class),
        currency=transaction.instrument.currency.code,
        kind=str(transaction.kind),
        trade_date=transaction.trade_date,
        quantity=transaction.quantity,
        price=transaction.price.amount,
        fees=transaction.fees.amount,
        notes=transaction.notes,
        created_at=transaction.created_at,
        updated_at=transaction.created_at,
    )


def transaction_to_domain(row: PortfolioTransactionRow) -> Transaction:
    currency = Currency.of(row.currency)
    return Transaction(
        id=row.id,
        instrument=InstrumentRef(
            instrument_id=row.instrument_id,
            symbol=row.symbol,
            asset_class=AssetClass(row.asset_class),
            currency=currency,
        ),
        kind=TransactionKind(row.kind),
        trade_date=row.trade_date,
        quantity=_decimal(row.quantity),
        price=Money(_decimal(row.price), currency),
        fees=Money(_decimal(row.fees), currency),
        notes=row.notes,
        created_at=row.created_at,
    )


def _decimal(value: Decimal | int | float) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


__all__ = [
    "apply_portfolio",
    "portfolio_to_domain",
    "portfolio_to_row",
    "target_to_row",
    "transaction_to_domain",
    "transaction_to_row",
]
