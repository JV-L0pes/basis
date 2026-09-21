"""Composition root for the analytics context."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from basis.kernel.infrastructure.http.dependencies import ClockDep
from basis.modules.analytics.application.use_cases import (
    GetAllocationAnalysis,
    GetBookOverview,
    GetPortfolioPerformance,
)
from basis.modules.market_data.domain.ports import MacroProvider, QuoteProvider
from basis.modules.market_data.presentation.dependencies import RuntimeDep
from basis.modules.portfolio.domain.ports import PortfolioReader
from basis.modules.portfolio.presentation.dependencies import PortfolioReaderDep


def get_quote_provider(runtime: RuntimeDep) -> QuoteProvider:
    return runtime.quotes


def get_macro_provider(runtime: RuntimeDep) -> MacroProvider:
    return runtime.macro


def get_portfolio_reader(reader: PortfolioReaderDep) -> PortfolioReader:
    return reader


QuotesDep = Annotated[QuoteProvider, Depends(get_quote_provider)]
MacroDep = Annotated[MacroProvider, Depends(get_macro_provider)]
ReaderDep = Annotated[PortfolioReader, Depends(get_portfolio_reader)]


def get_portfolio_performance(
    portfolios: ReaderDep,
    quotes: QuotesDep,
    macro: MacroDep,
    clock: ClockDep,
) -> GetPortfolioPerformance:
    return GetPortfolioPerformance(
        portfolios=portfolios, quotes=quotes, macro=macro, clock=clock
    )


def get_allocation_analysis(
    portfolios: ReaderDep,
    quotes: QuotesDep,
) -> GetAllocationAnalysis:
    return GetAllocationAnalysis(portfolios=portfolios, quotes=quotes)


def get_book_overview(portfolios: ReaderDep, quotes: QuotesDep) -> GetBookOverview:
    return GetBookOverview(portfolios=portfolios, quotes=quotes)


PerformanceDep = Annotated[GetPortfolioPerformance, Depends(get_portfolio_performance)]
AllocationDep = Annotated[GetAllocationAnalysis, Depends(get_allocation_analysis)]
BookOverviewDep = Annotated[GetBookOverview, Depends(get_book_overview)]


__all__ = [
    "AllocationDep",
    "BookOverviewDep",
    "PerformanceDep",
    "get_macro_provider",
    "get_quote_provider",
]
