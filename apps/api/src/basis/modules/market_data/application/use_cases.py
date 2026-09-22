"""Market data use cases."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from basis.kernel.application.pagination import MAX_PAGE_SIZE, encode_cursor
from basis.kernel.application.ports import UnitOfWork
from basis.kernel.domain.assets import AssetClass
from basis.kernel.domain.clock import Clock
from basis.kernel.domain.currency import Currency
from basis.kernel.domain.errors import NotFoundError, ValidationError
from basis.kernel.domain.events import EventPublisher
from basis.modules.market_data.application.dto import (
    InstrumentPage,
    InstrumentView,
    MarketOverview,
    PricePointDTO,
)
from basis.modules.market_data.domain.models import Instrument
from basis.modules.market_data.domain.ports import (
    IndexPointView,
    InstrumentCatalog,
    InstrumentRepository,
    MacroProvider,
    QuoteProvider,
    QuoteView,
)
from basis.modules.market_data.domain.value_objects import MacroSeriesCode, TickerSymbol
from basis.modules.market_data.infrastructure.providers.seed import SeedInstrument

DEFAULT_HISTORY_DAYS = 90


@dataclass(frozen=True, slots=True)
class SearchInstrumentsQuery:
    query: str | None = None
    asset_class: AssetClass | None = None
    limit: int = 20
    cursor: str | None = None


@dataclass(frozen=True, slots=True)
class PriceHistoryQuery:
    symbol: str
    start: date | None = None
    end: date | None = None


@dataclass(frozen=True, slots=True)
class MacroSeriesQuery:
    code: MacroSeriesCode
    start: date | None = None
    end: date | None = None


class SearchInstruments:
    """Search the instrument catalog with keyset pagination."""

    def __init__(self, *, instruments: InstrumentRepository) -> None:
        self._instruments = instruments

    async def execute(self, query: SearchInstrumentsQuery) -> InstrumentPage:
        limit = _validated_limit(query.limit)
        instruments, has_more = await self._instruments.list_page(
            limit=limit,
            cursor=query.cursor,
            query=query.query.strip() if query.query else None,
            asset_class=query.asset_class,
        )
        items = InstrumentView.from_entities(instruments)
        next_cursor = encode_cursor({"symbol": items[-1].symbol}) if has_more and items else None
        return InstrumentPage(items=items, next_cursor=next_cursor)


class GetInstrument:
    """Load one instrument by symbol."""

    def __init__(self, *, instruments: InstrumentRepository) -> None:
        self._instruments = instruments

    async def execute(self, symbol: str) -> InstrumentView:
        instrument = await self._instruments.get_by_symbol(symbol)
        if instrument is None:
            raise NotFoundError("Instrument not found", details={"symbol": symbol.upper()})
        return InstrumentView.from_entity(instrument)


class GetQuote:
    """Latest quote for a catalogued instrument."""

    def __init__(self, *, catalog: InstrumentCatalog, quotes: QuoteProvider) -> None:
        self._catalog = catalog
        self._quotes = quotes

    async def execute(self, symbol: str) -> QuoteView | None:
        instrument = await self._catalog.require_by_symbol(symbol)
        return await self._quotes.get_quote(instrument.symbol)


class GetQuotes:
    """Batch quote lookup keyed by symbol."""

    def __init__(self, *, quotes: QuoteProvider) -> None:
        self._quotes = quotes

    async def execute(self, symbols: Sequence[str]) -> dict[str, QuoteView]:
        normalized = [TickerSymbol(symbol).value for symbol in symbols]
        if len(normalized) > 50:
            raise ValidationError(
                "At most 50 symbols per request", details={"count": len(normalized)}
            )
        quotes = await self._quotes.get_quotes(normalized)
        return dict(quotes)


class GetPriceHistory:
    """Daily closes for a catalogued instrument, clamped to the configured window."""

    def __init__(
        self,
        *,
        catalog: InstrumentCatalog,
        quotes: QuoteProvider,
        clock: Clock,
        max_history_days: int = 1825,
    ) -> None:
        self._catalog = catalog
        self._quotes = quotes
        self._clock = clock
        self._max_history_days = max_history_days

    async def execute(self, query: PriceHistoryQuery) -> list[PricePointDTO]:
        instrument = await self._catalog.require_by_symbol(query.symbol)
        end = query.end or self._clock.today()
        start = query.start or (end - timedelta(days=DEFAULT_HISTORY_DAYS))
        if end < start:
            raise ValidationError("End date must not precede start date")
        if (end - start).days > self._max_history_days:
            start = end - timedelta(days=self._max_history_days)

        points = await self._quotes.get_history(instrument.symbol, start=start, end=end)
        return [
            PricePointDTO(
                date=point.date, close=point.close.amount, currency=point.close.currency.code
            )
            for point in points
        ]


class GetMacroSeries:
    """Macro series (Selic, CDI, IPCA, USD/BRL)."""

    def __init__(self, *, macro: MacroProvider, clock: Clock) -> None:
        self._macro = macro
        self._clock = clock

    async def execute(self, query: MacroSeriesQuery) -> list[IndexPointView]:
        end = query.end or self._clock.today()
        start = query.start or (end - timedelta(days=365))
        if end < start:
            raise ValidationError("End date must not precede start date")
        series = await self._macro.get_series(query.code, start=start, end=end)
        return list(series)


class GetMarketOverview:
    """Dashboard snapshot, resilient to unavailable series and symbols."""

    def __init__(
        self,
        *,
        quotes: QuoteProvider,
        macro: MacroProvider,
        symbols: Sequence[str] = (),
    ) -> None:
        self._quotes = quotes
        self._macro = macro
        self._symbols = tuple(symbols)

    async def execute(self) -> MarketOverview:
        macro_points: list[IndexPointView] = []
        for code in MacroSeriesCode:
            try:
                latest = await self._macro.latest(code)
            except Exception:  # noqa: BLE001 — a missing indicator must not break the dashboard
                latest = None
            if latest is not None:
                macro_points.append(latest)

        quotes: list[QuoteView] = []
        try:
            batch = await self._quotes.get_quotes(self._symbols)
        except Exception:  # noqa: BLE001 — quotes are optional for the dashboard
            batch = {}
        quotes = list(batch.values())

        ordered = sorted(
            [quote for quote in quotes if quote.change_percent is not None],
            key=lambda item: item.change_percent or Decimal(0),
            reverse=True,
        )
        gainers = ordered[:5]
        losers = list(reversed(ordered[-5:]))

        return MarketOverview(macro=macro_points, quotes=quotes, gainers=gainers, losers=losers)


class SyncInstrumentCatalog:
    """Idempotently register the reference instruments of the platform."""

    def __init__(
        self,
        *,
        instruments: InstrumentRepository,
        clock: Clock,
        uow: UnitOfWork,
        events: EventPublisher,
    ) -> None:
        self._instruments = instruments
        self._clock = clock
        self._uow = uow
        self._events = events

    async def execute(self, entries: Sequence[SeedInstrument]) -> int:
        created = 0
        recorded_events: list[object] = []
        for entry in entries:
            symbol = TickerSymbol(entry.symbol)
            if await self._instruments.get_by_symbol(str(symbol)) is not None:
                continue
            instrument = Instrument.register(
                symbol=symbol,
                name=entry.name,
                asset_class=entry.asset_class,
                currency=Currency.of(entry.currency_code),
                clock=self._clock,
            )
            await self._instruments.add(instrument)
            recorded_events.extend(instrument.pull_events())
            created += 1

        if created:
            await self._uow.commit()
            await self._events.publish(recorded_events)  # type: ignore[arg-type]
        return created


def _validated_limit(limit: int) -> int:
    if limit < 1:
        raise ValidationError("Page size must be at least 1", details={"limit": limit})
    return min(limit, MAX_PAGE_SIZE)


__all__ = [
    "DEFAULT_HISTORY_DAYS",
    "GetInstrument",
    "GetMacroSeries",
    "GetMarketOverview",
    "GetPriceHistory",
    "GetQuote",
    "GetQuotes",
    "MacroSeriesQuery",
    "PriceHistoryQuery",
    "SearchInstruments",
    "SearchInstrumentsQuery",
    "SyncInstrumentCatalog",
]
