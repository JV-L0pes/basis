"""Composition root for the market data context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from basis.config import Settings
from basis.kernel.domain.clock import SystemClock
from basis.kernel.infrastructure.http.dependencies import (
    ClockDep,
    EventBusDep,
    SessionDep,
    SettingsDep,
    UnitOfWorkDep,
)
from basis.modules.market_data.application.use_cases import (
    GetInstrument,
    GetMacroSeries,
    GetMarketOverview,
    GetPriceHistory,
    GetQuote,
    GetQuotes,
    SearchInstruments,
    SyncInstrumentCatalog,
)
from basis.modules.market_data.domain.ports import (
    InstrumentCatalog,
    InstrumentRepository,
    MacroProvider,
    QuoteProvider,
)
from basis.modules.market_data.infrastructure.providers.router import (
    MarketDataProviders,
    build_market_data_providers,
)
from basis.modules.market_data.infrastructure.providers.seed import SeedQuoteProvider
from basis.modules.market_data.infrastructure.repository import (
    SqlAlchemyInstrumentCatalog,
    SqlAlchemyInstrumentRepository,
)


@dataclass(frozen=True, slots=True)
class MarketDataRuntime:
    """Process-wide market data services, built once at application startup."""

    quotes: QuoteProvider
    macro: MacroProvider
    seed: SeedQuoteProvider


def build_market_data_runtime(settings: Settings) -> MarketDataRuntime:
    providers: MarketDataProviders = build_market_data_providers(
        clock=SystemClock(),
        timeout_seconds=settings.market_data.http_timeout_seconds,
        quote_cache_ttl_seconds=settings.market_data.quote_cache_ttl_seconds,
        brapi_token=(
            settings.market_data.brapi_token.get_secret_value()
            if settings.market_data.brapi_token
            else None
        ),
        allow_live_providers=settings.market_data.allow_live_providers,
    )
    return MarketDataRuntime(
        quotes=providers.quotes, macro=providers.macro, seed=providers.seed
    )


def get_market_data_runtime(request: Request) -> MarketDataRuntime:
    runtime: MarketDataRuntime = request.app.state.market_data_runtime
    return runtime


RuntimeDep = Annotated[MarketDataRuntime, Depends(get_market_data_runtime)]


def get_instrument_repository(session: SessionDep) -> InstrumentRepository:
    return SqlAlchemyInstrumentRepository(session)


def get_instrument_catalog(session: SessionDep) -> InstrumentCatalog:
    return SqlAlchemyInstrumentCatalog(session)


InstrumentRepoDep = Annotated[InstrumentRepository, Depends(get_instrument_repository)]
InstrumentCatalogDep = Annotated[InstrumentCatalog, Depends(get_instrument_catalog)]


def get_search_instruments(instruments: InstrumentRepoDep) -> SearchInstruments:
    return SearchInstruments(instruments=instruments)


def get_get_instrument(instruments: InstrumentRepoDep) -> GetInstrument:
    return GetInstrument(instruments=instruments)


def get_get_quote(runtime: RuntimeDep, catalog: InstrumentCatalogDep) -> GetQuote:
    return GetQuote(catalog=catalog, quotes=runtime.quotes)


def get_get_quotes(runtime: RuntimeDep) -> GetQuotes:
    return GetQuotes(quotes=runtime.quotes)


def get_get_price_history(
    runtime: RuntimeDep,
    catalog: InstrumentCatalogDep,
    clock: ClockDep,
    settings: SettingsDep,
) -> GetPriceHistory:
    return GetPriceHistory(
        catalog=catalog,
        quotes=runtime.quotes,
        clock=clock,
        max_history_days=settings.market_data.max_history_days,
    )


def get_get_macro_series(runtime: RuntimeDep, clock: ClockDep) -> GetMacroSeries:
    return GetMacroSeries(macro=runtime.macro, clock=clock)


async def get_get_market_overview(
    runtime: RuntimeDep,
    instruments: InstrumentRepoDep,
) -> GetMarketOverview:
    symbols = await instruments.list_active_symbols()
    return GetMarketOverview(quotes=runtime.quotes, macro=runtime.macro, symbols=symbols)


def get_sync_instrument_catalog(
    instruments: InstrumentRepoDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
    events: EventBusDep,
) -> SyncInstrumentCatalog:
    return SyncInstrumentCatalog(instruments=instruments, clock=clock, uow=uow, events=events)


SearchInstrumentsDep = Annotated[SearchInstruments, Depends(get_search_instruments)]
GetInstrumentDep = Annotated[GetInstrument, Depends(get_get_instrument)]
GetQuoteDep = Annotated[GetQuote, Depends(get_get_quote)]
GetQuotesDep = Annotated[GetQuotes, Depends(get_get_quotes)]
GetPriceHistoryDep = Annotated[GetPriceHistory, Depends(get_get_price_history)]
GetMacroSeriesDep = Annotated[GetMacroSeries, Depends(get_get_macro_series)]
GetMarketOverviewDep = Annotated[GetMarketOverview, Depends(get_get_market_overview)]
SyncInstrumentCatalogDep = Annotated[
    SyncInstrumentCatalog, Depends(get_sync_instrument_catalog)
]


__all__ = [
    "GetInstrumentDep",
    "GetMacroSeriesDep",
    "GetMarketOverviewDep",
    "GetPriceHistoryDep",
    "GetQuoteDep",
    "GetQuotesDep",
    "InstrumentCatalogDep",
    "MarketDataRuntime",
    "SearchInstrumentsDep",
    "SyncInstrumentCatalogDep",
    "build_market_data_runtime",
    "get_instrument_catalog",
    "get_instrument_repository",
]
