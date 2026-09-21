"""Integration tests: clients repositories against a real PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from basis.kernel.domain.clock import FrozenClock
from basis.kernel.domain.errors import NotFoundError
from basis.modules.clients.domain.models import Client
from basis.modules.clients.domain.ports import ClientCursor
from basis.modules.clients.domain.value_objects import (
    ClientStatus,
    ContactEmail,
    PersonName,
    SuitabilityAssessment,
    SuitabilityProfile,
    TaxId,
)
from basis.modules.clients.infrastructure.repository import (
    SqlAlchemyClientDirectory,
    SqlAlchemyClientRepository,
)

pytestmark = pytest.mark.integration

MOMENT = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)

TAX_IDS = [
    "52998224725",
    "11144477735",
    "12345678909",
    "39053344705",
    "86288366757",
    "15773967073",
    "44373125031",
]

NAMES = [
    "Alice Prado",
    "Bruno Lima",
    "Carla Dias",
    "Diego Alves",
    "Elisa Moraes",
    "Felipe Nunes",
    "Gabriela Reis",
]


def make_client(
    *,
    name: str = "Ana Souza",
    email: str = "ana@basis.dev",
    tax_id: str = "52998224725",
    moment: datetime = MOMENT,
    notes: str | None = "Private banking",
    answers: tuple[int, ...] = (2, 2, 2, 2, 2),
) -> Client:
    return Client.register(
        name=PersonName(name),
        email=ContactEmail(email),
        tax_id=TaxId(tax_id),
        assessment=SuitabilityAssessment(answers=answers),
        notes=notes,
        clock=FrozenClock(moment),
    )


class TestClientRepository:
    async def test_add_and_get_roundtrip(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyClientRepository(db_session)
        client = make_client()
        await repository.add(client)

        loaded = await repository.get(client.id)

        assert loaded is not None
        assert str(loaded.name) == "Ana Souza"
        assert str(loaded.email) == "ana@basis.dev"
        assert loaded.tax_id == client.tax_id
        assert loaded.tax_id.kind.value == "cpf"
        assert loaded.suitability is SuitabilityProfile.MODERATE
        assert loaded.suitability_score == 50
        assert loaded.status is ClientStatus.ACTIVE
        assert loaded.notes == "Private banking"
        assert loaded.created_at == client.created_at

    async def test_get_returns_none_for_unknown_id(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyClientRepository(db_session)
        assert await repository.get(uuid4()) is None

    async def test_get_by_tax_id_normalizes_punctuation(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyClientRepository(db_session)
        await repository.add(make_client())

        found = await repository.get_by_tax_id(TaxId("529.982.247-25"))
        missing = await repository.get_by_tax_id(TaxId("11144477735"))

        assert found is not None
        assert found.tax_id == TaxId("52998224725")
        assert missing is None

    async def test_update_persists_changes(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyClientRepository(db_session)
        client = make_client()
        await repository.add(client)

        clock = FrozenClock(MOMENT + timedelta(days=1))
        client.update_details(
            name=PersonName("Ana Maria Souza"),
            email=ContactEmail("ana.maria@basis.dev"),
            notes=None,
            clock=clock,
        )
        client.assess_suitability(SuitabilityAssessment(answers=(4, 4, 4, 4, 4)), clock=clock)
        await repository.update(client)

        loaded = await repository.get(client.id)
        assert loaded is not None
        assert str(loaded.name) == "Ana Maria Souza"
        assert str(loaded.email) == "ana.maria@basis.dev"
        assert loaded.notes is None
        assert loaded.suitability is SuitabilityProfile.AGGRESSIVE
        assert loaded.updated_at == MOMENT + timedelta(days=1)

    async def test_update_missing_client_raises(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyClientRepository(db_session)
        with pytest.raises(NotFoundError):
            await repository.update(make_client())

    async def test_duplicate_tax_id_is_surfaced_as_integrity_error(
        self, db_session: AsyncSession
    ) -> None:
        repository = SqlAlchemyClientRepository(db_session)
        await repository.add(make_client())

        with pytest.raises(IntegrityError):
            async with db_session.begin_nested():
                await repository.add(make_client(email="outra@basis.dev"))

    async def test_list_page_is_empty_for_an_empty_table(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyClientRepository(db_session)
        items, has_more = await repository.list_page(limit=10)
        assert list(items) == []
        assert has_more is False

    async def test_cursor_pagination_across_three_pages(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyClientRepository(db_session)
        for index, tax_id in enumerate(TAX_IDS):
            await repository.add(
                make_client(
                    name=NAMES[index],
                    email=f"cliente{index}@basis.dev",
                    tax_id=tax_id,
                    moment=MOMENT + timedelta(minutes=index),
                )
            )

        first, first_has_more = await repository.list_page(limit=3)
        assert [str(client.name) for client in first] == [
            "Gabriela Reis",
            "Felipe Nunes",
            "Elisa Moraes",
        ]
        assert first_has_more is True

        second, second_has_more = await repository.list_page(limit=3, cursor=_cursor(first[-1]))
        assert [str(client.name) for client in second] == [
            "Diego Alves",
            "Carla Dias",
            "Bruno Lima",
        ]
        assert second_has_more is True

        third, third_has_more = await repository.list_page(limit=3, cursor=_cursor(second[-1]))
        assert [str(client.name) for client in third] == ["Alice Prado"]
        assert third_has_more is False

    async def test_list_page_filters_by_query_and_status(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyClientRepository(db_session)
        ana = make_client(name="Ana Souza", email="ana@basis.dev")
        bruno = make_client(
            name="Bruno Lima",
            email="bruno@empresa.com.br",
            tax_id="11144477735",
            moment=MOMENT + timedelta(minutes=1),
        )
        await repository.add(ana)
        await repository.add(bruno)
        bruno.archive(clock=FrozenClock(MOMENT + timedelta(minutes=2)))
        await repository.update(bruno)

        by_name, _ = await repository.list_page(limit=10, query="souza")
        assert [str(client.name) for client in by_name] == ["Ana Souza"]

        by_email, _ = await repository.list_page(limit=10, query="EMPRESA")
        assert [str(client.name) for client in by_email] == ["Bruno Lima"]

        archived, _ = await repository.list_page(limit=10, status=ClientStatus.ARCHIVED)
        assert [str(client.name) for client in archived] == ["Bruno Lima"]

        active, _ = await repository.list_page(limit=10, status=ClientStatus.ACTIVE)
        assert [str(client.name) for client in active] == ["Ana Souza"]

    async def test_query_wildcards_are_escaped(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyClientRepository(db_session)
        await repository.add(make_client(name="Ana Souza"))
        await repository.add(
            make_client(
                name="Bruno Lima",
                email="bruno@basis.dev",
                tax_id="11144477735",
                moment=MOMENT + timedelta(minutes=1),
            )
        )

        everything, _ = await repository.list_page(limit=10, query="%")
        assert list(everything) == []

    async def test_count_by_status(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyClientRepository(db_session)
        ana = make_client()
        bruno = make_client(
            name="Bruno Lima",
            email="bruno@basis.dev",
            tax_id="11144477735",
            moment=MOMENT + timedelta(minutes=1),
        )
        await repository.add(ana)
        await repository.add(bruno)
        bruno.archive(clock=FrozenClock(MOMENT + timedelta(minutes=2)))
        await repository.update(bruno)

        counts = await repository.count_by_status()

        assert counts[ClientStatus.ACTIVE] == 1
        assert counts[ClientStatus.ARCHIVED] == 1


class TestClientDirectory:
    async def test_summary_contains_only_the_published_fields(
        self, db_session: AsyncSession
    ) -> None:
        repository = SqlAlchemyClientRepository(db_session)
        client = make_client()
        await repository.add(client)

        directory = SqlAlchemyClientDirectory(db_session)
        summary = await directory.get_client_summary(client.id)

        assert summary is not None
        assert summary.id == client.id
        assert summary.name == "Ana Souza"
        assert summary.status == "active"
        assert summary.suitability == "moderate"

    async def test_unknown_client_returns_none(self, db_session: AsyncSession) -> None:
        directory = SqlAlchemyClientDirectory(db_session)
        assert await directory.get_client_summary(uuid4()) is None

    async def test_require_client_raises_not_found(self, db_session: AsyncSession) -> None:
        directory = SqlAlchemyClientDirectory(db_session)
        with pytest.raises(NotFoundError, match="Client not found"):
            await directory.require_client(uuid4())

    async def test_require_client_returns_summary(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyClientRepository(db_session)
        client = make_client()
        await repository.add(client)

        directory = SqlAlchemyClientDirectory(db_session)
        summary = await directory.require_client(client.id)

        assert summary.id == client.id


def _cursor(client: Client) -> ClientCursor:
    return ClientCursor(created_at=client.created_at, id=client.id)
