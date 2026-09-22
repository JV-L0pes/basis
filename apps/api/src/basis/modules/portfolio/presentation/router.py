"""Portfolio HTTP endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from basis.modules.identity.presentation.dependencies import CurrentUserDep, ManagerDep
from basis.modules.portfolio.application.use_cases import (
    ListPortfoliosQuery,
    OpenPortfolioCommand,
    RecordTransactionCommand,
    RenamePortfolioCommand,
    SetTargetsCommand,
)
from basis.modules.portfolio.domain.value_objects import PortfolioStatus
from basis.modules.portfolio.presentation.dependencies import (
    ArchivePortfolioDep,
    GetPortfolioDep,
    GetTransactionsDep,
    ListPortfoliosDep,
    OpenPortfolioDep,
    RecordTransactionDep,
    RenamePortfolioDep,
    SetTargetsDep,
)
from basis.modules.portfolio.presentation.schemas import (
    OpenPortfolioRequest,
    PortfolioListResponse,
    PortfolioResponse,
    RecordTransactionRequest,
    RenamePortfolioRequest,
    SetTargetsRequest,
    TransactionResponse,
)

router = APIRouter(prefix="/portfolios", tags=["portfolios"])


@router.get(
    "",
    response_model=PortfolioListResponse,
    summary="List portfolios with client/status filters and cursor pagination",
)
async def list_portfolios(
    use_case: ListPortfoliosDep,
    user: CurrentUserDep,
    client_id: Annotated[UUID | None, Query()] = None,
    status_filter: Annotated[PortfolioStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=200)] = None,
) -> PortfolioListResponse:
    page = await use_case.execute(
        ListPortfoliosQuery(client_id=client_id, status=status_filter, limit=limit, cursor=cursor)
    )
    return PortfolioListResponse.from_page(page)


@router.post(
    "",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Open a portfolio for a client",
)
async def open_portfolio(
    payload: OpenPortfolioRequest,
    use_case: OpenPortfolioDep,
    user: ManagerDep,
) -> PortfolioResponse:
    view = await use_case.execute(
        OpenPortfolioCommand(
            client_id=payload.client_id,
            name=payload.name,
            base_currency=payload.base_currency,
        )
    )
    return PortfolioResponse.from_view(view)


@router.get(
    "/{portfolio_id}",
    response_model=PortfolioResponse,
    summary="Get a portfolio with its current valuation",
)
async def get_portfolio(
    portfolio_id: UUID,
    use_case: GetPortfolioDep,
    user: CurrentUserDep,
) -> PortfolioResponse:
    return PortfolioResponse.from_view(await use_case.execute(portfolio_id))


@router.patch("/{portfolio_id}", response_model=PortfolioResponse, summary="Rename a portfolio")
async def rename_portfolio(
    portfolio_id: UUID,
    payload: RenamePortfolioRequest,
    use_case: RenamePortfolioDep,
    user: ManagerDep,
) -> PortfolioResponse:
    view = await use_case.execute(
        RenamePortfolioCommand(portfolio_id=portfolio_id, name=payload.name)
    )
    return PortfolioResponse.from_view(view)


@router.put(
    "/{portfolio_id}/targets",
    response_model=PortfolioResponse,
    summary="Set the strategic allocation targets (weights in basis points)",
)
async def set_targets(
    portfolio_id: UUID,
    payload: SetTargetsRequest,
    use_case: SetTargetsDep,
    user: ManagerDep,
) -> PortfolioResponse:
    view = await use_case.execute(
        SetTargetsCommand(
            portfolio_id=portfolio_id,
            targets=[(target.asset_class, target.weight_bps) for target in payload.targets],
        )
    )
    return PortfolioResponse.from_view(view)


@router.post(
    "/{portfolio_id}/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a transaction in the portfolio ledger",
)
async def record_transaction(
    portfolio_id: UUID,
    payload: RecordTransactionRequest,
    use_case: RecordTransactionDep,
    user: ManagerDep,
) -> TransactionResponse:
    view = await use_case.execute(
        RecordTransactionCommand(
            portfolio_id=portfolio_id,
            symbol=payload.symbol,
            kind=payload.kind,
            trade_date=payload.trade_date,
            quantity=payload.quantity,
            price=payload.price,
            fees=payload.fees,
            notes=payload.notes,
        )
    )
    return TransactionResponse.from_view(view)


@router.get(
    "/{portfolio_id}/transactions",
    response_model=list[TransactionResponse],
    summary="List the portfolio ledger",
)
async def list_transactions(
    portfolio_id: UUID,
    use_case: GetTransactionsDep,
    user: CurrentUserDep,
) -> list[TransactionResponse]:
    return [TransactionResponse.from_view(view) for view in await use_case.execute(portfolio_id)]


@router.post(
    "/{portfolio_id}/archive", response_model=PortfolioResponse, summary="Archive a portfolio"
)
async def archive_portfolio(
    portfolio_id: UUID,
    use_case: ArchivePortfolioDep,
    user: ManagerDep,
) -> PortfolioResponse:
    return PortfolioResponse.from_view(await use_case.execute(portfolio_id))


__all__ = ["router"]
