"""Market data HTTP endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from basis.kernel.domain.assets import AssetClass
from basis.kernel.domain.errors import NotFoundError
from basis.modules.identity.presentation.dependencies import CurrentUserDep
from basis.modules.market_data.application.use_cases import (
    MacroSeriesQuery,
    PriceHistoryQuery,
    SearchInstrumentsQuery,
)
from basis.modules.market_data.domain.value_objects import MacroSeriesCode
from basis.modules.market_data.presentation.dependencies import (
    GetInstrumentDep,
    GetMacroSeriesDep,
    GetMarketOverviewDep,
    GetPriceHistoryDep,
    GetQuoteDep,
    GetQuotesDep,
    SearchInstrumentsDep,
)
from basis.modules.market_data.presentation.schemas import (
    InstrumentListResponse,
    InstrumentResponse,
    MacroPointResponse,
    MarketOverviewResponse,
    PricePointResponse,
    QuoteResponse,
)

router = APIRouter(tags=["market"])


@router.get(
    "/instruments",
    response_model=InstrumentListResponse,
    summary="Search the instrument catalog",
)
async def list_instruments(
    use_case: SearchInstrumentsDep,
    user: CurrentUserDep,
    query: Annotated[str | None, Query(max_length=120)] = None,
    asset_class: Annotated[AssetClass | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
) -> InstrumentListResponse:
    page = await use_case.execute(
        SearchInstrumentsQuery(
            query=query, asset_class=asset_class, limit=limit, cursor=cursor
        )
    )
    return InstrumentListResponse.from_page(page)


@router.get(
    "/instruments/{symbol}", response_model=InstrumentResponse, summary="Get an instrument"
)
async def get_instrument(
    symbol: str,
    use_case: GetInstrumentDep,
    user: CurrentUserDep,
) -> InstrumentResponse:
    return InstrumentResponse.from_view(await use_case.execute(symbol))


@router.get(
    "/instruments/{symbol}/quote",
    response_model=QuoteResponse,
    summary="Latest quote for an instrument",
)
async def get_quote(
    symbol: str,
    use_case: GetQuoteDep,
    user: CurrentUserDep,
) -> QuoteResponse:
    quote = await use_case.execute(symbol)
    if quote is None:
        raise NotFoundError("No quote available", details={"symbol": symbol.upper()})
    return QuoteResponse.from_quote(quote)


@router.get(
    "/instruments/{symbol}/history",
    response_model=list[PricePointResponse],
    summary="Daily close history for an instrument",
)
async def get_history(
    symbol: str,
    use_case: GetPriceHistoryDep,
    user: CurrentUserDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> list[PricePointResponse]:
    points = await use_case.execute(PriceHistoryQuery(symbol=symbol, start=start, end=end))
    return [PricePointResponse.from_dto(point) for point in points]


@router.get(
    "/quotes",
    response_model=list[QuoteResponse],
    summary="Batch quote lookup (comma-separated symbols)",
)
async def get_quotes(
    use_case: GetQuotesDep,
    user: CurrentUserDep,
    symbols: Annotated[str, Query(description="Comma-separated symbols, e.g. PETR4,VALE3")],
) -> list[QuoteResponse]:
    parsed = [item.strip() for item in symbols.split(",") if item.strip()]
    quotes = await use_case.execute(parsed)
    return [QuoteResponse.from_quote(quote) for quote in quotes.values()]


@router.get(
    "/market/macro/{code}",
    response_model=list[MacroPointResponse],
    summary="Macro series from the Brazilian Central Bank",
)
async def get_macro_series(
    code: MacroSeriesCode,
    use_case: GetMacroSeriesDep,
    user: CurrentUserDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> list[MacroPointResponse]:
    points = await use_case.execute(MacroSeriesQuery(code=code, start=start, end=end))
    return [MacroPointResponse.from_point(point) for point in points]


@router.get(
    "/market/overview",
    response_model=MarketOverviewResponse,
    summary="Dashboard snapshot: macro indicators and blue-chip quotes",
)
async def market_overview(
    use_case: GetMarketOverviewDep,
    user: CurrentUserDep,
) -> MarketOverviewResponse:
    return MarketOverviewResponse.from_overview(await use_case.execute())


__all__ = ["router"]
