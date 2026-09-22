"""Composition root for the portfolio context."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from basis.kernel.infrastructure.http.dependencies import (
    ClockDep,
    EventBusDep,
    SessionDep,
    UnitOfWorkDep,
)
from basis.modules.clients.domain.ports import ClientDirectory
from basis.modules.clients.presentation.dependencies import ClientDirectoryDep
from basis.modules.market_data.domain.ports import InstrumentCatalog, QuoteProvider
from basis.modules.market_data.presentation.dependencies import (
    InstrumentCatalogDep,
    RuntimeDep,
)
from basis.modules.portfolio.application.use_cases import (
    ArchivePortfolio,
    GetPortfolio,
    GetPortfolioTransactions,
    ListPortfolios,
    OpenPortfolio,
    RecordTransaction,
    RenamePortfolio,
    SetAllocationTargets,
)
from basis.modules.portfolio.domain.ports import PortfolioReader, PortfolioRepository
from basis.modules.portfolio.infrastructure.repository import (
    SqlAlchemyPortfolioReader,
    SqlAlchemyPortfolioRepository,
)


def get_portfolio_repository(session: SessionDep) -> PortfolioRepository:
    return SqlAlchemyPortfolioRepository(session)


def get_portfolio_reader(session: SessionDep) -> PortfolioReader:
    return SqlAlchemyPortfolioReader(session)


def get_quote_provider(runtime: RuntimeDep) -> QuoteProvider:
    return runtime.quotes


def get_instrument_catalog(catalog: InstrumentCatalogDep) -> InstrumentCatalog:
    return catalog


def get_client_directory(directory: ClientDirectoryDep) -> ClientDirectory:
    return directory


PortfolioRepoDep = Annotated[PortfolioRepository, Depends(get_portfolio_repository)]
PortfolioReaderDep = Annotated[PortfolioReader, Depends(get_portfolio_reader)]
QuotesDep = Annotated[QuoteProvider, Depends(get_quote_provider)]
CatalogDep = Annotated[InstrumentCatalog, Depends(get_instrument_catalog)]
DirectoryDep = Annotated[ClientDirectory, Depends(get_client_directory)]


def get_open_portfolio(
    portfolios: PortfolioRepoDep,
    clients: DirectoryDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
    events: EventBusDep,
) -> OpenPortfolio:
    return OpenPortfolio(
        portfolios=portfolios, clients=clients, clock=clock, uow=uow, events=events
    )


def get_rename_portfolio(
    portfolios: PortfolioRepoDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
) -> RenamePortfolio:
    return RenamePortfolio(portfolios=portfolios, clock=clock, uow=uow)


def get_set_targets(
    portfolios: PortfolioRepoDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
    events: EventBusDep,
) -> SetAllocationTargets:
    return SetAllocationTargets(portfolios=portfolios, clock=clock, uow=uow, events=events)


def get_record_transaction(
    portfolios: PortfolioRepoDep,
    instruments: CatalogDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
    events: EventBusDep,
) -> RecordTransaction:
    return RecordTransaction(
        portfolios=portfolios,
        instruments=instruments,
        clock=clock,
        uow=uow,
        events=events,
    )


def get_archive_portfolio(
    portfolios: PortfolioRepoDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
    events: EventBusDep,
) -> ArchivePortfolio:
    return ArchivePortfolio(portfolios=portfolios, clock=clock, uow=uow, events=events)


def get_get_portfolio(
    portfolios: PortfolioRepoDep,
    quotes: QuotesDep,
) -> GetPortfolio:
    return GetPortfolio(portfolios=portfolios, quotes=quotes)


def get_list_portfolios(portfolios: PortfolioRepoDep, quotes: QuotesDep) -> ListPortfolios:
    return ListPortfolios(portfolios=portfolios, quotes=quotes)


def get_portfolio_transactions(portfolios: PortfolioRepoDep) -> GetPortfolioTransactions:
    return GetPortfolioTransactions(portfolios=portfolios)


OpenPortfolioDep = Annotated[OpenPortfolio, Depends(get_open_portfolio)]
RenamePortfolioDep = Annotated[RenamePortfolio, Depends(get_rename_portfolio)]
SetTargetsDep = Annotated[SetAllocationTargets, Depends(get_set_targets)]
RecordTransactionDep = Annotated[RecordTransaction, Depends(get_record_transaction)]
ArchivePortfolioDep = Annotated[ArchivePortfolio, Depends(get_archive_portfolio)]
GetPortfolioDep = Annotated[GetPortfolio, Depends(get_get_portfolio)]
ListPortfoliosDep = Annotated[ListPortfolios, Depends(get_list_portfolios)]
GetTransactionsDep = Annotated[GetPortfolioTransactions, Depends(get_portfolio_transactions)]


__all__ = [
    "ArchivePortfolioDep",
    "GetPortfolioDep",
    "GetTransactionsDep",
    "ListPortfoliosDep",
    "OpenPortfolioDep",
    "PortfolioReaderDep",
    "PortfolioRepoDep",
    "RecordTransactionDep",
    "RenamePortfolioDep",
    "SetTargetsDep",
    "get_portfolio_reader",
    "get_portfolio_repository",
]
