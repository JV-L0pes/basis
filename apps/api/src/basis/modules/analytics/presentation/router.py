"""Analytics HTTP endpoints."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from basis.modules.analytics.presentation.dependencies import (
    AllocationDep,
    BookOverviewDep,
    PerformanceDep,
)
from basis.modules.analytics.presentation.schemas import (
    AllocationAnalysisResponse,
    BookOverviewResponse,
    PerformanceResponse,
)
from basis.modules.identity.presentation.dependencies import CurrentUserDep

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/portfolios/{portfolio_id}/performance",
    response_model=PerformanceResponse,
    summary="Time-weighted and money-weighted performance with risk metrics",
)
async def portfolio_performance(
    portfolio_id: UUID,
    use_case: PerformanceDep,
    user: CurrentUserDep,
    start: Annotated[date | None, Query()] = None,
    end: Annotated[date | None, Query()] = None,
) -> PerformanceResponse:
    report = await use_case.execute(portfolio_id, start=start, end=end)
    return PerformanceResponse.from_report(report)


@router.get(
    "/portfolios/{portfolio_id}/allocation",
    response_model=AllocationAnalysisResponse,
    summary="Allocation, drift against targets and rebalancing plan",
)
async def portfolio_allocation(
    portfolio_id: UUID,
    use_case: AllocationDep,
    user: CurrentUserDep,
) -> AllocationAnalysisResponse:
    analysis = await use_case.execute(portfolio_id)
    return AllocationAnalysisResponse.from_analysis(analysis)


@router.get(
    "/book",
    response_model=BookOverviewResponse,
    summary="Aggregated view of every portfolio (AUM and allocation)",
)
async def book_overview(
    use_case: BookOverviewDep,
    user: CurrentUserDep,
) -> BookOverviewResponse:
    return BookOverviewResponse.from_overview(await use_case.execute())


__all__ = ["router"]
