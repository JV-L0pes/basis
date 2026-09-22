"""Portfolio use cases."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from basis.kernel.application.pagination import MAX_PAGE_SIZE
from basis.kernel.application.ports import UnitOfWork
from basis.kernel.domain.assets import AssetClass
from basis.kernel.domain.clock import Clock
from basis.kernel.domain.currency import Currency
from basis.kernel.domain.errors import NotFoundError, ValidationError
from basis.kernel.domain.events import EventPublisher
from basis.kernel.domain.money import Money
from basis.modules.clients.domain.ports import ClientDirectory
from basis.modules.market_data.domain.ports import InstrumentCatalog, QuoteProvider
from basis.modules.portfolio.application.dto import (
    PortfolioPage,
    PortfolioView,
    TransactionView,
)
from basis.modules.portfolio.domain.models import Portfolio, Transaction
from basis.modules.portfolio.domain.ports import PortfolioCursor, PortfolioRepository
from basis.modules.portfolio.domain.valuation import valuate
from basis.modules.portfolio.domain.value_objects import (
    AllocationTargets,
    InstrumentRef,
    PortfolioStatus,
    TargetAllocation,
    TransactionKind,
)


@dataclass(frozen=True, slots=True)
class OpenPortfolioCommand:
    client_id: UUID
    name: str
    base_currency: str = "BRL"


@dataclass(frozen=True, slots=True)
class RenamePortfolioCommand:
    portfolio_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class SetTargetsCommand:
    portfolio_id: UUID
    targets: Sequence[tuple[str, int]]


@dataclass(frozen=True, slots=True)
class RecordTransactionCommand:
    portfolio_id: UUID
    symbol: str
    kind: str
    trade_date: date
    quantity: Decimal
    price: Decimal
    fees: Decimal | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class ListPortfoliosQuery:
    client_id: UUID | None = None
    status: PortfolioStatus | None = None
    limit: int = 20
    cursor: str | None = None


class OpenPortfolio:
    """Open a portfolio for an existing client."""

    def __init__(
        self,
        *,
        portfolios: PortfolioRepository,
        clients: ClientDirectory,
        clock: Clock,
        uow: UnitOfWork,
        events: EventPublisher,
    ) -> None:
        self._portfolios = portfolios
        self._clients = clients
        self._clock = clock
        self._uow = uow
        self._events = events

    async def execute(self, command: OpenPortfolioCommand) -> PortfolioView:
        client = await self._clients.require_client(command.client_id)
        if client.status != "active":
            raise ValidationError(
                "Cannot open a portfolio for an archived client",
                details={"client_id": str(command.client_id)},
            )
        portfolio = Portfolio.open(
            client_id=command.client_id,
            name=command.name,
            base_currency=Currency.of(command.base_currency),
            clock=self._clock,
        )
        await self._portfolios.add(portfolio)

        events = portfolio.pull_events()
        await self._uow.commit()
        await self._events.publish(events)
        return PortfolioView.from_entity(portfolio)


class RenamePortfolio:
    """Rename a portfolio."""

    def __init__(
        self,
        *,
        portfolios: PortfolioRepository,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._portfolios = portfolios
        self._clock = clock
        self._uow = uow

    async def execute(self, command: RenamePortfolioCommand) -> PortfolioView:
        portfolio = await _require_portfolio(self._portfolios, command.portfolio_id)
        portfolio.rename(command.name, clock=self._clock)
        await self._portfolios.update(portfolio)
        await self._uow.commit()
        return PortfolioView.from_entity(portfolio)


class SetAllocationTargets:
    """Define the strategic allocation (weights in basis points)."""

    def __init__(
        self,
        *,
        portfolios: PortfolioRepository,
        clock: Clock,
        uow: UnitOfWork,
        events: EventPublisher,
    ) -> None:
        self._portfolios = portfolios
        self._clock = clock
        self._uow = uow
        self._events = events

    async def execute(self, command: SetTargetsCommand) -> PortfolioView:
        portfolio = await _require_portfolio(self._portfolios, command.portfolio_id)
        targets = AllocationTargets(
            [
                TargetAllocation(asset_class=_parse_asset_class(name), weight_bps=weight)
                for name, weight in command.targets
            ]
        )
        portfolio.set_targets(targets, clock=self._clock)
        await self._portfolios.update(portfolio)

        events = portfolio.pull_events()
        await self._uow.commit()
        await self._events.publish(events)
        return PortfolioView.from_entity(portfolio)


class RecordTransaction:
    """Record a buy, sell, dividend, interest or fee in the ledger."""

    def __init__(
        self,
        *,
        portfolios: PortfolioRepository,
        instruments: InstrumentCatalog,
        clock: Clock,
        uow: UnitOfWork,
        events: EventPublisher,
    ) -> None:
        self._portfolios = portfolios
        self._instruments = instruments
        self._clock = clock
        self._uow = uow
        self._events = events

    async def execute(self, command: RecordTransactionCommand) -> TransactionView:
        portfolio = await _require_portfolio(self._portfolios, command.portfolio_id)
        instrument = await self._instruments.require_by_symbol(command.symbol)
        kind = _parse_transaction_kind(command.kind)

        instrument_ref = InstrumentRef(
            instrument_id=instrument.id,
            symbol=instrument.symbol,
            asset_class=instrument.asset_class,
            currency=instrument.currency,
        )
        transaction = Transaction.record(
            instrument=instrument_ref,
            kind=kind,
            trade_date=command.trade_date,
            quantity=command.quantity,
            price=Money(command.price, instrument.currency),
            fees=Money(command.fees, instrument.currency) if command.fees is not None else None,
            notes=command.notes,
            clock=self._clock,
        )
        portfolio.record_transaction(transaction, clock=self._clock)
        await self._portfolios.update(portfolio)

        events = portfolio.pull_events()
        await self._uow.commit()
        await self._events.publish(events)
        return TransactionView.from_entity(transaction)


class ArchivePortfolio:
    """Archive a portfolio (soft delete)."""

    def __init__(
        self,
        *,
        portfolios: PortfolioRepository,
        clock: Clock,
        uow: UnitOfWork,
        events: EventPublisher,
    ) -> None:
        self._portfolios = portfolios
        self._clock = clock
        self._uow = uow
        self._events = events

    async def execute(self, portfolio_id: UUID) -> PortfolioView:
        portfolio = await _require_portfolio(self._portfolios, portfolio_id)
        portfolio.archive(clock=self._clock)
        await self._portfolios.update(portfolio)

        events = portfolio.pull_events()
        await self._uow.commit()
        await self._events.publish(events)
        return PortfolioView.from_entity(portfolio)


class GetPortfolio:
    """Load a portfolio and value it against the latest quotes."""

    def __init__(
        self,
        *,
        portfolios: PortfolioRepository,
        quotes: QuoteProvider,
    ) -> None:
        self._portfolios = portfolios
        self._quotes = quotes

    async def execute(self, portfolio_id: UUID) -> PortfolioView:
        portfolio = await _require_portfolio(self._portfolios, portfolio_id)
        prices = await _prices_for(portfolio, self._quotes)
        return PortfolioView.from_entity(portfolio, valuation=valuate(portfolio, prices))


class GetPortfolioTransactions:
    """List the transactions of a portfolio, oldest first."""

    def __init__(self, *, portfolios: PortfolioRepository) -> None:
        self._portfolios = portfolios

    async def execute(self, portfolio_id: UUID) -> list[TransactionView]:
        portfolio = await _require_portfolio(self._portfolios, portfolio_id)
        return [
            TransactionView.from_entity(transaction) for transaction in portfolio.transactions
        ]


class ListPortfolios:
    """List portfolios with optional client/status filters and keyset pagination.

    The page is marked to market with a single batch of quotes, so list screens
    show value, result and return without a round trip per portfolio.
    """

    def __init__(self, *, portfolios: PortfolioRepository, quotes: QuoteProvider) -> None:
        self._portfolios = portfolios
        self._quotes = quotes

    async def execute(self, query: ListPortfoliosQuery) -> PortfolioPage:
        if query.limit < 1:
            raise ValidationError("Page size must be at least 1", details={"limit": query.limit})
        limit = min(query.limit, MAX_PAGE_SIZE)
        cursor = PortfolioCursor.decode(query.cursor) if query.cursor else None

        portfolios, has_more = await self._portfolios.list_page(
            limit=limit, cursor=cursor, client_id=query.client_id, status=query.status
        )

        symbols = sorted(
            {
                instrument.symbol
                for portfolio in portfolios
                for instrument in portfolio.instruments()
            }
        )
        quotes = await self._quotes.get_quotes(symbols) if symbols else {}
        prices: dict[str, Money] = {symbol: quote.price for symbol, quote in quotes.items()}

        items = [
            PortfolioView.from_entity(portfolio, valuation=valuate(portfolio, prices))
            for portfolio in portfolios
        ]
        next_cursor: str | None = None
        if has_more and portfolios:
            last = portfolios[-1]
            next_cursor = PortfolioCursor(created_at=last.created_at, id=last.id).encode()
        return PortfolioPage(items=items, next_cursor=next_cursor)


def _parse_asset_class(value: str) -> AssetClass:
    try:
        return AssetClass(value.strip().lower())
    except ValueError as exc:
        raise ValidationError(
            "Unknown asset class", details={"asset_class": value}
        ) from exc


def _parse_transaction_kind(value: str) -> TransactionKind:
    try:
        return TransactionKind(value.strip().lower())
    except ValueError as exc:
        raise ValidationError(
            "Unknown transaction kind", details={"kind": value}
        ) from exc


async def _require_portfolio(
    portfolios: PortfolioRepository, portfolio_id: UUID
) -> Portfolio:
    portfolio = await portfolios.get(portfolio_id)
    if portfolio is None:
        raise NotFoundError("Portfolio not found", details={"portfolio_id": str(portfolio_id)})
    return portfolio


async def _prices_for(portfolio: Portfolio, quotes: QuoteProvider) -> Mapping[str, Money]:
    """Latest prices for every instrument the portfolio ever traded."""
    symbols = [instrument.symbol for instrument in portfolio.instruments()]
    if not symbols:
        return {}
    batch = await quotes.get_quotes(symbols)
    return {symbol: quote.price for symbol, quote in batch.items()}


__all__ = [
    "ArchivePortfolio",
    "GetPortfolio",
    "GetPortfolioTransactions",
    "ListPortfolios",
    "ListPortfoliosQuery",
    "OpenPortfolio",
    "OpenPortfolioCommand",
    "RecordTransaction",
    "RecordTransactionCommand",
    "RenamePortfolio",
    "RenamePortfolioCommand",
    "SetAllocationTargets",
    "SetTargetsCommand",
]
