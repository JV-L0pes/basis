"""Composition root for the clients context."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from basis.kernel.infrastructure.http.dependencies import (
    ClockDep,
    EventBusDep,
    SessionDep,
    UnitOfWorkDep,
)
from basis.modules.clients.application.use_cases import (
    ArchiveClient,
    AssessClientSuitability,
    GetClient,
    ListClients,
    ReactivateClient,
    RegisterClient,
    UpdateClientDetails,
)
from basis.modules.clients.domain.ports import ClientDirectory, ClientRepository
from basis.modules.clients.infrastructure.repository import (
    SqlAlchemyClientDirectory,
    SqlAlchemyClientRepository,
)


def get_client_repository(session: SessionDep) -> ClientRepository:
    return SqlAlchemyClientRepository(session)


def get_client_directory(session: SessionDep) -> ClientDirectory:
    return SqlAlchemyClientDirectory(session)


ClientRepoDep = Annotated[ClientRepository, Depends(get_client_repository)]
ClientDirectoryDep = Annotated[ClientDirectory, Depends(get_client_directory)]


def get_register_client(
    clients: ClientRepoDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
    events: EventBusDep,
) -> RegisterClient:
    return RegisterClient(clients=clients, clock=clock, uow=uow, events=events)


def get_update_client(
    clients: ClientRepoDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
) -> UpdateClientDetails:
    return UpdateClientDetails(clients=clients, clock=clock, uow=uow)


def get_assess_suitability(
    clients: ClientRepoDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
    events: EventBusDep,
) -> AssessClientSuitability:
    return AssessClientSuitability(clients=clients, clock=clock, uow=uow, events=events)


def get_archive_client(
    clients: ClientRepoDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
    events: EventBusDep,
) -> ArchiveClient:
    return ArchiveClient(clients=clients, clock=clock, uow=uow, events=events)


def get_reactivate_client(
    clients: ClientRepoDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
) -> ReactivateClient:
    return ReactivateClient(clients=clients, clock=clock, uow=uow)


def get_get_client(clients: ClientRepoDep) -> GetClient:
    return GetClient(clients=clients)


def get_list_clients(clients: ClientRepoDep) -> ListClients:
    return ListClients(clients=clients)


RegisterClientDep = Annotated[RegisterClient, Depends(get_register_client)]
UpdateClientDep = Annotated[UpdateClientDetails, Depends(get_update_client)]
AssessSuitabilityDep = Annotated[AssessClientSuitability, Depends(get_assess_suitability)]
ArchiveClientDep = Annotated[ArchiveClient, Depends(get_archive_client)]
ReactivateClientDep = Annotated[ReactivateClient, Depends(get_reactivate_client)]
GetClientDep = Annotated[GetClient, Depends(get_get_client)]
ListClientsDep = Annotated[ListClients, Depends(get_list_clients)]


__all__ = [
    "ArchiveClientDep",
    "AssessSuitabilityDep",
    "ClientDirectoryDep",
    "GetClientDep",
    "ListClientsDep",
    "ReactivateClientDep",
    "RegisterClientDep",
    "UpdateClientDep",
    "get_client_directory",
    "get_client_repository",
]
