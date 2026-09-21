"""SQLAlchemy repositories for the portfolio context."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from basis.kernel.domain.errors import NotFoundError
from basis.modules.portfolio.domain.models import Portfolio, Transaction
from basis.modules.portfolio.domain.ports import (
    PortfolioCursor,
    PortfolioSnapshot,
    PositionSnapshot,
    TargetWeight,
    TransactionSnapshot,
)
from basis.modules.portfolio.domain.value_objects import PortfolioStatus
from basis.modules.portfolio.infrastructure.mappers import (
    apply_portfolio,
    portfolio_to_domain,
    portfolio_to_row,
    target_to_row,
    transaction_to_row,
)
from basis.modules.portfolio.infrastructure.models import (
    PortfolioRow,
    PortfolioTargetRow,
    PortfolioTransactionRow,
)


class SqlAlchemyPortfolioRepository:
    """Portfolio aggregate persistence backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, portfolio_id: UUID) -> Portfolio | None:
        row = await self._session.get(PortfolioRow, portfolio_id)
        if row is None:
            return None
        targets = await self._load_targets(portfolio_id)
        transactions = await self._load_transactions(portfolio_id)
        return portfolio_to_domain(row, targets, transactions)

    async def add(self, portfolio: Portfolio) -> None:
        self._session.add(portfolio_to_row(portfolio))
        await self._session.flush()
        self._add_children(portfolio)
        await self._session.flush()

    async def update(self, portfolio: Portfolio) -> None:
        row = await self._session.get(PortfolioRow, portfolio.id)
        if row is None:
            raise NotFoundError(
                "Portfolio not found", details={"portfolio_id": str(portfolio.id)}
            )
        apply_portfolio(portfolio, row)

        await self._session.execute(
            delete(PortfolioTargetRow).where(
                PortfolioTargetRow.portfolio_id == portfolio.id
            )
        )
        for target in portfolio.targets:
            self._session.add(target_to_row(target, portfolio.id))

        await self._sync_transactions(portfolio)
        await self._session.flush()

    async def list_page(
        self,
        *,
        limit: int,
        cursor: PortfolioCursor | None = None,
        client_id: UUID | None = None,
        status: PortfolioStatus | None = None,
    ) -> tuple[Sequence[Portfolio], bool]:
        filters = []
        if client_id is not None:
            filters.append(PortfolioRow.client_id == client_id)
        if status is not None:
            filters.append(PortfolioRow.status == str(status))
        if cursor is not None:
            filters.append(
                tuple_(PortfolioRow.created_at, PortfolioRow.id)
                < (cursor.created_at, cursor.id)
            )

        statement = (
            select(PortfolioRow)
            .where(*filters)
            .order_by(PortfolioRow.created_at.desc(), PortfolioRow.id.desc())
            .limit(limit + 1)
        )
        rows = (await self._session.execute(statement)).scalars().all()
        has_more = len(rows) > limit

        portfolios: list[Portfolio] = []
        for row in rows[:limit]:
            targets = await self._load_targets(row.id)
            transactions = await self._load_transactions(row.id)
            portfolios.append(portfolio_to_domain(row, targets, transactions))
        return portfolios, has_more

    async def count_for_client(self, client_id: UUID) -> int:
        result = await self._session.execute(
            select(func.count())
            .select_from(PortfolioRow)
            .where(PortfolioRow.client_id == client_id)
        )
        return int(result.scalar_one())

    async def all_ids(self) -> Sequence[UUID]:
        result = await self._session.execute(select(PortfolioRow.id).order_by(PortfolioRow.id))
        return list(result.scalars().all())

    # -- internals --------------------------------------------------------
    def _add_children(self, portfolio: Portfolio) -> None:
        for target in portfolio.targets:
            self._session.add(target_to_row(target, portfolio.id))
        for transaction in portfolio.transactions:
            self._session.add(transaction_to_row(transaction, portfolio.id))

    async def _sync_transactions(self, portfolio: Portfolio) -> None:
        """Transactions are append-only: insert the new, delete the removed."""
        existing_ids = set(
            (
                await self._session.execute(
                    select(PortfolioTransactionRow.id).where(
                        PortfolioTransactionRow.portfolio_id == portfolio.id
                    )
                )
            )
            .scalars()
            .all()
        )
        desired = {transaction.id for transaction in portfolio.transactions}
        if existing_ids - desired:
            await self._session.execute(
                delete(PortfolioTransactionRow).where(
                    PortfolioTransactionRow.id.in_(existing_ids - desired)
                )
            )
        for transaction in portfolio.transactions:
            if transaction.id not in existing_ids:
                self._session.add(transaction_to_row(transaction, portfolio.id))

    async def _load_targets(self, portfolio_id: UUID) -> Sequence[PortfolioTargetRow]:
        result = await self._session.execute(
            select(PortfolioTargetRow).where(PortfolioTargetRow.portfolio_id == portfolio_id)
        )
        return result.scalars().all()

    async def _load_transactions(self, portfolio_id: UUID) -> Sequence[PortfolioTransactionRow]:
        result = await self._session.execute(
            select(PortfolioTransactionRow)
            .where(PortfolioTransactionRow.portfolio_id == portfolio_id)
            .order_by(
                PortfolioTransactionRow.trade_date.asc(),
                PortfolioTransactionRow.created_at.asc(),
                PortfolioTransactionRow.id.asc(),
            )
        )
        return result.scalars().all()


class SqlAlchemyPortfolioReader:
    """Published read-only view: fully-folded portfolio snapshots."""

    def __init__(self, session: AsyncSession) -> None:
        self._repository = SqlAlchemyPortfolioRepository(session)

    async def get_snapshot(self, portfolio_id: UUID) -> PortfolioSnapshot | None:
        portfolio = await self._repository.get(portfolio_id)
        return _to_snapshot(portfolio) if portfolio is not None else None

    async def list_snapshots(
        self, *, limit: int = 100, client_id: UUID | None = None
    ) -> Sequence[PortfolioSnapshot]:
        portfolios, _ = await self._repository.list_page(limit=limit, client_id=client_id)
        return [_to_snapshot(portfolio) for portfolio in portfolios]


def _to_snapshot(portfolio: Portfolio) -> PortfolioSnapshot:
    return PortfolioSnapshot(
        id=portfolio.id,
        client_id=portfolio.client_id,
        name=portfolio.name,
        base_currency=portfolio.base_currency.code,
        status=str(portfolio.status),
        targets=tuple(
            TargetWeight(asset_class=str(target.asset_class), weight_bps=target.weight_bps)
            for target in portfolio.targets
        ),
        positions=tuple(
            PositionSnapshot(
                symbol=position.instrument.symbol,
                asset_class=str(position.instrument.asset_class),
                currency=position.instrument.currency.code,
                quantity=position.quantity,
                average_cost=position.average_cost.amount,
                cost_basis=position.cost_basis.amount,
                realized_gain=position.realized_gain.amount,
                income=position.income.amount,
                costs=position.costs.amount,
            )
            for position in portfolio.positions()
        ),
        transactions=tuple(
            _transaction_snapshot(transaction) for transaction in portfolio.transactions
        ),
        created_at=portfolio.created_at,
    )


def _transaction_snapshot(transaction: Transaction) -> TransactionSnapshot:
    return TransactionSnapshot(
        id=transaction.id,
        symbol=transaction.instrument.symbol,
        asset_class=str(transaction.instrument.asset_class),
        currency=transaction.instrument.currency.code,
        kind=str(transaction.kind),
        trade_date=transaction.trade_date,
        quantity=transaction.quantity,
        price=transaction.price.amount,
        fees=transaction.fees.amount,
    )


__all__ = ["SqlAlchemyPortfolioReader", "SqlAlchemyPortfolioRepository"]
