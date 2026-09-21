"""Clients use cases."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from basis.kernel.application.pagination import MAX_PAGE_SIZE
from basis.kernel.application.ports import UnitOfWork
from basis.kernel.domain.clock import Clock
from basis.kernel.domain.errors import ConflictError, NotFoundError, ValidationError
from basis.kernel.domain.events import EventPublisher
from basis.modules.clients.application.dto import ClientPage, ClientView
from basis.modules.clients.domain.models import UNSET, Client, _Unset
from basis.modules.clients.domain.ports import ClientCursor, ClientRepository
from basis.modules.clients.domain.value_objects import (
    ClientStatus,
    ContactEmail,
    PersonName,
    SuitabilityAssessment,
    TaxId,
)


@dataclass(frozen=True, slots=True)
class RegisterClientCommand:
    name: str
    email: str
    tax_id: str
    notes: str | None = None
    suitability_answers: list[int] | None = None


@dataclass(frozen=True, slots=True)
class UpdateClientDetailsCommand:
    client_id: UUID
    name: str | None = None
    email: str | None = None
    notes: str | _Unset | None = UNSET


@dataclass(frozen=True, slots=True)
class AssessClientSuitabilityCommand:
    client_id: UUID
    answers: list[int]


@dataclass(frozen=True, slots=True)
class ListClientsQuery:
    query: str | None = None
    status: ClientStatus | None = None
    limit: int = 20
    cursor: str | None = None


class RegisterClient:
    """Register an investor. The tax id must be unique."""

    def __init__(
        self,
        *,
        clients: ClientRepository,
        clock: Clock,
        uow: UnitOfWork,
        events: EventPublisher,
    ) -> None:
        self._clients = clients
        self._clock = clock
        self._uow = uow
        self._events = events

    async def execute(self, command: RegisterClientCommand) -> ClientView:
        tax_id = TaxId(command.tax_id)
        if await self._clients.get_by_tax_id(tax_id) is not None:
            raise ConflictError(
                "A client with this tax id is already registered",
                details={"tax_id": tax_id.masked},
            )

        assessment = (
            SuitabilityAssessment.from_scores(command.suitability_answers)
            if command.suitability_answers
            else SuitabilityAssessment.neutral()
        )
        client = Client.register(
            name=PersonName(command.name),
            email=ContactEmail(command.email),
            tax_id=tax_id,
            assessment=assessment,
            notes=command.notes,
            clock=self._clock,
        )
        await self._clients.add(client)

        events = client.pull_events()
        await self._uow.commit()
        await self._events.publish(events)
        return ClientView.from_entity(client)


class UpdateClientDetails:
    """Update the mutable contact fields of a client."""

    def __init__(
        self,
        *,
        clients: ClientRepository,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._clients = clients
        self._clock = clock
        self._uow = uow

    async def execute(self, command: UpdateClientDetailsCommand) -> ClientView:
        client = await _require_client(self._clients, command.client_id)
        client.update_details(
            name=PersonName(command.name) if command.name is not None else None,
            email=ContactEmail(command.email) if command.email is not None else None,
            notes=command.notes,
            clock=self._clock,
        )
        await self._clients.update(client)
        await self._uow.commit()
        return ClientView.from_entity(client)


class AssessClientSuitability:
    """Re-assess the client's risk profile from a new questionnaire."""

    def __init__(
        self,
        *,
        clients: ClientRepository,
        clock: Clock,
        uow: UnitOfWork,
        events: EventPublisher,
    ) -> None:
        self._clients = clients
        self._clock = clock
        self._uow = uow
        self._events = events

    async def execute(self, command: AssessClientSuitabilityCommand) -> ClientView:
        client = await _require_client(self._clients, command.client_id)
        client.assess_suitability(
            SuitabilityAssessment.from_scores(command.answers), clock=self._clock
        )
        await self._clients.update(client)

        events = client.pull_events()
        await self._uow.commit()
        await self._events.publish(events)
        return ClientView.from_entity(client)


class ArchiveClient:
    """Archive a client (soft delete). Idempotent."""

    def __init__(
        self,
        *,
        clients: ClientRepository,
        clock: Clock,
        uow: UnitOfWork,
        events: EventPublisher,
    ) -> None:
        self._clients = clients
        self._clock = clock
        self._uow = uow
        self._events = events

    async def execute(self, client_id: UUID) -> ClientView:
        client = await _require_client(self._clients, client_id)
        client.archive(clock=self._clock)
        await self._clients.update(client)

        events = client.pull_events()
        await self._uow.commit()
        await self._events.publish(events)
        return ClientView.from_entity(client)


class ReactivateClient:
    """Reactivate a previously archived client. Idempotent."""

    def __init__(
        self,
        *,
        clients: ClientRepository,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._clients = clients
        self._clock = clock
        self._uow = uow

    async def execute(self, client_id: UUID) -> ClientView:
        client = await _require_client(self._clients, client_id)
        client.reactivate(clock=self._clock)
        await self._clients.update(client)
        await self._uow.commit()
        return ClientView.from_entity(client)


class GetClient:
    """Load a single client."""

    def __init__(self, *, clients: ClientRepository) -> None:
        self._clients = clients

    async def execute(self, client_id: UUID) -> ClientView:
        return ClientView.from_entity(await _require_client(self._clients, client_id))


class ListClients:
    """List clients with search, status filter and keyset pagination."""

    def __init__(self, *, clients: ClientRepository) -> None:
        self._clients = clients

    async def execute(self, query: ListClientsQuery) -> ClientPage:
        if query.limit < 1:
            raise ValidationError("Page size must be at least 1", details={"limit": query.limit})
        limit = min(query.limit, MAX_PAGE_SIZE)
        cursor = ClientCursor.decode(query.cursor) if query.cursor else None

        clients, has_more = await self._clients.list_page(
            limit=limit,
            cursor=cursor,
            query=query.query.strip() if query.query else None,
            status=query.status,
        )
        items = ClientView.from_entities(clients)
        next_cursor: str | None = None
        if has_more and clients:
            last = clients[-1]
            next_cursor = ClientCursor(created_at=last.created_at, id=last.id).encode()
        return ClientPage(items=items, next_cursor=next_cursor)


async def _require_client(clients: ClientRepository, client_id: UUID) -> Client:
    client = await clients.get(client_id)
    if client is None:
        raise NotFoundError("Client not found", details={"client_id": str(client_id)})
    return client


__all__ = [
    "ArchiveClient",
    "AssessClientSuitability",
    "AssessClientSuitabilityCommand",
    "GetClient",
    "ListClients",
    "ListClientsQuery",
    "ReactivateClient",
    "RegisterClient",
    "RegisterClientCommand",
    "UpdateClientDetails",
    "UpdateClientDetailsCommand",
]
