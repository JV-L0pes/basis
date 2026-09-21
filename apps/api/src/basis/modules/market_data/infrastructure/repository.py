"""SQLAlchemy repositories for the market data context."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from basis.kernel.application.pagination import decode_cursor
from basis.kernel.domain.assets import AssetClass
from basis.kernel.domain.currency import Currency
from basis.kernel.domain.errors import NotFoundError
from basis.modules.market_data.domain.models import Instrument
from basis.modules.market_data.domain.ports import InstrumentSummary
from basis.modules.market_data.infrastructure.mappers import (
    apply_instrument,
    instrument_to_domain,
    instrument_to_row,
)
from basis.modules.market_data.infrastructure.models import InstrumentRow


class SqlAlchemyInstrumentRepository:
    """Instrument catalog persistence backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, instrument_id: UUID) -> Instrument | None:
        row = await self._session.get(InstrumentRow, instrument_id)
        return instrument_to_domain(row) if row is not None else None

    async def get_by_symbol(self, symbol: str) -> Instrument | None:
        result = await self._session.execute(
            select(InstrumentRow).where(InstrumentRow.symbol == symbol.strip().upper())
        )
        row = result.scalar_one_or_none()
        return instrument_to_domain(row) if row is not None else None

    async def add(self, instrument: Instrument) -> None:
        self._session.add(instrument_to_row(instrument))
        await self._session.flush()

    async def update(self, instrument: Instrument) -> None:
        row = await self._session.get(InstrumentRow, instrument.id)
        if row is None:
            raise NotFoundError(
                "Instrument not found", details={"instrument_id": str(instrument.id)}
            )
        apply_instrument(instrument, row)
        await self._session.flush()

    async def list_page(
        self,
        *,
        limit: int,
        cursor: str | None = None,
        query: str | None = None,
        asset_class: AssetClass | None = None,
    ) -> tuple[Sequence[Instrument], bool]:
        """Keyset pagination ordered by symbol. ``cursor`` is an opaque token."""
        filters = _filters(query, asset_class)
        if cursor:
            filters.append(InstrumentRow.symbol > decode_cursor(cursor)["symbol"])

        statement = (
            select(InstrumentRow)
            .where(*filters)
            .order_by(InstrumentRow.symbol.asc())
            .limit(limit + 1)
        )
        rows = (await self._session.execute(statement)).scalars().all()
        has_more = len(rows) > limit
        return [instrument_to_domain(row) for row in rows[:limit]], has_more

    async def list_active_symbols(self) -> Sequence[str]:
        result = await self._session.execute(
            select(InstrumentRow.symbol)
            .where(InstrumentRow.is_active.is_(True))
            .order_by(InstrumentRow.symbol.asc())
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(InstrumentRow))
        return int(result.scalar_one())


def _filters(query: str | None, asset_class: AssetClass | None) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = [InstrumentRow.is_active.is_(True)]
    if query:
        pattern = f"%{_escape_like(query)}%"
        filters.append(
            or_(
                InstrumentRow.symbol.ilike(pattern, escape="\\"),
                InstrumentRow.name.ilike(pattern, escape="\\"),
            )
        )
    if asset_class is not None:
        filters.append(InstrumentRow.asset_class == str(asset_class))
    return filters


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SqlAlchemyInstrumentCatalog:
    """Published read-only view of the instrument catalog."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_symbol(self, symbol: str) -> InstrumentSummary | None:
        result = await self._session.execute(
            select(InstrumentRow).where(InstrumentRow.symbol == symbol.strip().upper())
        )
        row = result.scalar_one_or_none()
        return _to_summary(row) if row is not None else None

    async def require_by_symbol(self, symbol: str) -> InstrumentSummary:
        summary = await self.get_by_symbol(symbol)
        if summary is None:
            raise NotFoundError("Instrument not found", details={"symbol": symbol.upper()})
        return summary


def _to_summary(row: InstrumentRow) -> InstrumentSummary:
    return InstrumentSummary(
        id=row.id,
        symbol=row.symbol,
        name=row.name,
        asset_class=AssetClass(row.asset_class),
        currency=Currency.of(row.currency),
    )


__all__ = ["SqlAlchemyInstrumentCatalog", "SqlAlchemyInstrumentRepository"]
