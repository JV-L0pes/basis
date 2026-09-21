"""Unit tests for clients use cases using in-memory doubles."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from basis.kernel.domain.clock import FrozenClock
from basis.kernel.domain.errors import (
    ConflictError,
    InvariantViolationError,
    NotFoundError,
    ValidationError,
)
from basis.modules.clients.application.use_cases import (
    ArchiveClient,
    AssessClientSuitability,
    AssessClientSuitabilityCommand,
    GetClient,
    ListClients,
    ListClientsQuery,
    ReactivateClient,
    RegisterClient,
    RegisterClientCommand,
    UpdateClientDetails,
    UpdateClientDetailsCommand,
)
from basis.modules.clients.domain.value_objects import ClientStatus, SuitabilityProfile
from tests.fakes import InMemoryClientRepository, NoopUnitOfWork, NullEventPublisher

MOMENT = datetime(2026, 3, 10, 9, 30, tzinfo=UTC)

TAX_IDS = {
    "ana": "52998224725",
    "bruno": "11144477735",
    "carla": "12345678909",
    "diego": "39053344705",
    "elisa": "86288366757",
    "felipe": "15773967073",
    "gabriela": "44373125031",
}

AGGRESSIVE_ANSWERS = [4, 4, 4, 4, 4]


class Harness:
    """Wires the clients use cases against in-memory doubles."""

    def __init__(self) -> None:
        self.clock = FrozenClock(MOMENT)
        self.clients = InMemoryClientRepository()
        self.events = NullEventPublisher()
        self.uow = NoopUnitOfWork()
        self.register = RegisterClient(
            clients=self.clients, clock=self.clock, uow=self.uow, events=self.events
        )
        self.update = UpdateClientDetails(clients=self.clients, clock=self.clock, uow=self.uow)
        self.assess = AssessClientSuitability(
            clients=self.clients, clock=self.clock, uow=self.uow, events=self.events
        )
        self.archive = ArchiveClient(
            clients=self.clients, clock=self.clock, uow=self.uow, events=self.events
        )
        self.reactivate = ReactivateClient(clients=self.clients, clock=self.clock, uow=self.uow)
        self.get = GetClient(clients=self.clients)
        self.list_clients = ListClients(clients=self.clients)


def register_command(
    name: str = "Ana Souza",
    email: str = "ana@basis.dev",
    tax_id: str = TAX_IDS["ana"],
    *,
    notes: str | None = "Private banking",
    answers: list[int] | None = None,
) -> RegisterClientCommand:
    return RegisterClientCommand(
        name=name,
        email=email,
        tax_id=tax_id,
        notes=notes,
        suitability_answers=answers,
    )


async def register_client(
    harness: Harness,
    key: str = "ana",
    *,
    name: str | None = None,
    answers: list[int] | None = None,
) -> None:
    await harness.register.execute(
        register_command(
            name=name or key.title(),
            email=f"{key}@basis.dev",
            tax_id=TAX_IDS[key],
            answers=answers,
        )
    )


class TestRegisterClient:
    async def test_registers_active_client_and_publishes_event(self) -> None:
        harness = Harness()
        view = await harness.register.execute(register_command(answers=AGGRESSIVE_ANSWERS))

        assert view.status == ClientStatus.ACTIVE.value
        assert view.suitability == SuitabilityProfile.AGGRESSIVE.value
        assert view.suitability_score == 100
        assert view.tax_id_masked == "***.***.247-25"
        assert harness.uow.commits == 1
        assert len(harness.events.published) == 1
        assert len(harness.clients.clients) == 1

    async def test_omitted_answers_default_to_a_neutral_assessment(self) -> None:
        harness = Harness()
        view = await harness.register.execute(register_command())
        assert view.suitability == SuitabilityProfile.MODERATE.value
        assert view.suitability_score == 50

    async def test_duplicate_tax_id_is_rejected(self) -> None:
        harness = Harness()
        await register_client(harness, "ana")
        with pytest.raises(ConflictError, match="already registered"):
            await register_client(harness, "ana", name="Outra Pessoa")

    async def test_duplicate_detection_normalizes_punctuation(self) -> None:
        harness = Harness()
        await harness.register.execute(register_command(tax_id="529.982.247-25"))
        with pytest.raises(ConflictError):
            await harness.register.execute(register_command(tax_id="52998224725"))

    async def test_invalid_tax_id_is_rejected(self) -> None:
        harness = Harness()
        with pytest.raises(ValidationError):
            await harness.register.execute(register_command(tax_id="52998224724"))


class TestUpdateClientDetails:
    async def test_partial_update_keeps_omitted_fields(self) -> None:
        harness = Harness()
        await register_client(harness, "ana")
        client = next(iter(harness.clients.clients.values()))

        view = await harness.update.execute(
            UpdateClientDetailsCommand(client_id=client.id, name="Ana Maria")
        )

        assert view.name == "Ana Maria"
        assert view.email == "ana@basis.dev"
        assert view.notes == "Private banking"
        assert harness.uow.commits == 2

    async def test_empty_notes_clear_the_field(self) -> None:
        harness = Harness()
        await register_client(harness, "ana")
        client = next(iter(harness.clients.clients.values()))

        view = await harness.update.execute(
            UpdateClientDetailsCommand(client_id=client.id, notes="  ")
        )

        assert view.notes is None

    async def test_unknown_client_raises_not_found(self) -> None:
        harness = Harness()
        with pytest.raises(NotFoundError):
            await harness.update.execute(UpdateClientDetailsCommand(client_id=uuid4()))

    async def test_archived_client_cannot_be_updated(self) -> None:
        harness = Harness()
        await register_client(harness, "ana")
        client = next(iter(harness.clients.clients.values()))
        await harness.archive.execute(client.id)

        with pytest.raises(InvariantViolationError, match="archived"):
            await harness.update.execute(
                UpdateClientDetailsCommand(client_id=client.id, name="Ana Maria")
            )


class TestAssessClientSuitability:
    async def test_reassessing_updates_profile_and_publishes_event(self) -> None:
        harness = Harness()
        await register_client(harness, "ana", answers=AGGRESSIVE_ANSWERS)
        client = next(iter(harness.clients.clients.values()))
        harness.events.published.clear()

        view = await harness.assess.execute(
            AssessClientSuitabilityCommand(client_id=client.id, answers=[0, 0, 0, 0, 0])
        )

        assert view.suitability == SuitabilityProfile.CONSERVATIVE.value
        assert view.suitability_score == 0
        assert len(harness.events.published) == 1

    async def test_archived_client_cannot_be_reassessed(self) -> None:
        harness = Harness()
        await register_client(harness, "ana")
        client = next(iter(harness.clients.clients.values()))
        await harness.archive.execute(client.id)

        with pytest.raises(InvariantViolationError, match="archived"):
            await harness.assess.execute(
                AssessClientSuitabilityCommand(client_id=client.id, answers=AGGRESSIVE_ANSWERS)
            )


class TestArchiveAndReactivate:
    async def test_archive_records_status_and_publishes_event_once(self) -> None:
        harness = Harness()
        await register_client(harness, "ana")
        client = next(iter(harness.clients.clients.values()))
        harness.events.published.clear()

        view = await harness.archive.execute(client.id)
        assert view.status == ClientStatus.ARCHIVED.value
        await harness.archive.execute(client.id)
        assert len(harness.events.published) == 1
        assert harness.uow.commits == 3

    async def test_reactivate_restores_active_status(self) -> None:
        harness = Harness()
        await register_client(harness, "ana")
        client = next(iter(harness.clients.clients.values()))
        await harness.archive.execute(client.id)

        view = await harness.reactivate.execute(client.id)

        assert view.status == ClientStatus.ACTIVE.value
        updated = await harness.update.execute(
            UpdateClientDetailsCommand(client_id=client.id, name="Ana Maria")
        )
        assert updated.name == "Ana Maria"

    async def test_unknown_clients_raise_not_found(self) -> None:
        harness = Harness()
        with pytest.raises(NotFoundError):
            await harness.archive.execute(uuid4())
        with pytest.raises(NotFoundError):
            await harness.reactivate.execute(uuid4())


class TestGetClient:
    async def test_returns_view(self) -> None:
        harness = Harness()
        await register_client(harness, "ana")
        client = next(iter(harness.clients.clients.values()))

        view = await harness.get.execute(client.id)

        assert view.name == "Ana"
        assert view.notes == "Private banking"

    async def test_unknown_client_raises_not_found(self) -> None:
        harness = Harness()
        with pytest.raises(NotFoundError):
            await harness.get.execute(uuid4())


class TestListClients:
    async def test_paginates_in_descending_creation_order(self) -> None:
        harness = Harness()
        for key in TAX_IDS:
            await register_client(harness, key)
            harness.clock.advance(timedelta(minutes=1))

        first = await harness.list_clients.execute(ListClientsQuery(limit=3))
        assert [item.name for item in first.items] == ["Gabriela", "Felipe", "Elisa"]
        assert first.next_cursor is not None

        second = await harness.list_clients.execute(
            ListClientsQuery(limit=3, cursor=first.next_cursor)
        )
        assert [item.name for item in second.items] == ["Diego", "Carla", "Bruno"]
        assert second.next_cursor is not None

        third = await harness.list_clients.execute(
            ListClientsQuery(limit=3, cursor=second.next_cursor)
        )
        assert [item.name for item in third.items] == ["Ana"]
        assert third.next_cursor is None

    async def test_page_size_is_clamped_to_the_kernel_maximum(self) -> None:
        harness = Harness()
        await register_client(harness, "ana")
        page = await harness.list_clients.execute(ListClientsQuery(limit=1000))
        assert len(page.items) == 1

    async def test_query_filters_by_name_or_email(self) -> None:
        harness = Harness()
        await register_client(harness, "ana", name="Ana Souza")
        await register_client(harness, "bruno", name="Bruno Lima")
        harness.clock.advance(timedelta(minutes=1))

        by_name = await harness.list_clients.execute(ListClientsQuery(query="lima"))
        assert [item.name for item in by_name.items] == ["Bruno Lima"]

        by_email = await harness.list_clients.execute(ListClientsQuery(query="ana@"))
        assert [item.name for item in by_email.items] == ["Ana Souza"]

    async def test_status_filter(self) -> None:
        harness = Harness()
        await register_client(harness, "ana")
        await register_client(harness, "bruno")
        target = next(
            client for client in harness.clients.clients.values() if str(client.name) == "Bruno"
        )
        await harness.archive.execute(target.id)

        archived = await harness.list_clients.execute(
            ListClientsQuery(status=ClientStatus.ARCHIVED)
        )
        assert [item.name for item in archived.items] == ["Bruno"]

        active = await harness.list_clients.execute(ListClientsQuery(status=ClientStatus.ACTIVE))
        assert [item.name for item in active.items] == ["Ana"]

    async def test_malformed_cursor_is_rejected(self) -> None:
        harness = Harness()
        with pytest.raises(ValidationError, match="cursor"):
            await harness.list_clients.execute(ListClientsQuery(cursor="not-a-cursor"))

    async def test_count_by_status(self) -> None:
        harness = Harness()
        await register_client(harness, "ana")
        await register_client(harness, "bruno")
        target = next(
            client for client in harness.clients.clients.values() if str(client.name) == "Bruno"
        )
        await harness.archive.execute(target.id)

        counts = await harness.clients.count_by_status()
        assert counts[ClientStatus.ACTIVE] == 1
        assert counts[ClientStatus.ARCHIVED] == 1
