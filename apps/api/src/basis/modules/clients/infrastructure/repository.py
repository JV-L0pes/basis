"""SQLAlchemy repositories for the clients context."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from basis.kernel.domain.errors import NotFoundError
from basis.modules.clients.domain.models import Client
from basis.modules.clients.domain.ports import ClientCursor, ClientSummary
from basis.modules.clients.domain.value_objects import ClientStatus, TaxId
from basis.modules.clients.infrastructure.mappers import (
    apply_client,
    client_to_domain,
    client_to_row,
)
from basis.modules.clients.infrastructure.models import ClientRow


class SqlAlchemyClientRepository:
    """Client persistence backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, client_id: UUID) -> Client | None:
        row = await self._session.get(ClientRow, client_id)
        return client_to_domain(row) if row is not None else None

    async def get_by_tax_id(self, tax_id: TaxId) -> Client | None:
        result = await self._session.execute(
            select(ClientRow).where(ClientRow.tax_id == tax_id.value)
        )
        row = result.scalar_one_or_none()
        return client_to_domain(row) if row is not None else None

    async def add(self, client: Client) -> None:
        self._session.add(client_to_row(client))
        await self._session.flush()

    async def update(self, client: Client) -> None:
        row = await self._session.get(ClientRow, client.id)
        if row is None:
            raise NotFoundError("Client not found", details={"client_id": str(client.id)})
        apply_client(client, row)
        await self._session.flush()

    async def list_page(
        self,
        *,
        limit: int,
        cursor: ClientCursor | None = None,
        query: str | None = None,
        status: ClientStatus | None = None,
    ) -> tuple[Sequence[Client], bool]:
        """Keyset pagination ordered by (created_at, id) descending."""
        filters = _filters(query, status)
        if cursor is not None:
            filters.append(
                tuple_(ClientRow.created_at, ClientRow.id)
                < (cursor.created_at, cursor.id)
            )

        statement = (
            select(ClientRow)
            .where(*filters)
            .order_by(ClientRow.created_at.desc(), ClientRow.id.desc())
            .limit(limit + 1)
        )
        rows = (await self._session.execute(statement)).scalars().all()
        has_more = len(rows) > limit
        return [client_to_domain(row) for row in rows[:limit]], has_more

    async def count_by_status(self) -> Mapping[ClientStatus, int]:
        result = await self._session.execute(
            select(ClientRow.status, func.count()).group_by(ClientRow.status)
        )
        counts: dict[ClientStatus, int] = {}
        for status_value, total in result.all():
            counts[ClientStatus(status_value)] = int(total)
        return counts


def _filters(query: str | None, status: ClientStatus | None) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []
    if query:
        pattern = f"%{_escape_like(query)}%"
        filters.append(
            or_(
                ClientRow.name.ilike(pattern, escape="\\"),
                ClientRow.email.ilike(pattern, escape="\\"),
            )
        )
    if status is not None:
        filters.append(ClientRow.status == str(status))
    return filters


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SqlAlchemyClientDirectory:
    """Read-only, cross-context view of clients."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_client_summary(self, client_id: UUID) -> ClientSummary | None:
        row = await self._session.get(ClientRow, client_id)
        if row is None:
            return None
        return ClientSummary(
            id=row.id,
            name=row.name,
            status=row.status,
            suitability=row.suitability,
        )

    async def require_client(self, client_id: UUID) -> ClientSummary:
        summary = await self.get_client_summary(client_id)
        if summary is None:
            raise NotFoundError("Client not found", details={"client_id": str(client_id)})
        return summary


__all__ = ["SqlAlchemyClientDirectory", "SqlAlchemyClientRepository"]
