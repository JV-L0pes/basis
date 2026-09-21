"""Integration tests: market-data repositories against a real PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from basis.kernel.application.pagination import encode_cursor
from basis.kernel.domain.assets import AssetClass
from basis.kernel.domain.clock import FrozenClock
from basis.kernel.domain.currency import BRL
from basis.kernel.domain.errors import NotFoundError
from basis.modules.market_data.domain.models import Instrument
from basis.modules.market_data.domain.value_objects import (
    CfiCode,
    Isin,
    Mic,
    TickerSymbol,
)
from basis.modules.market_data.infrastructure.repository import (
    SqlAlchemyInstrumentCatalog,
    SqlAlchemyInstrumentRepository,
)

pytestmark = pytest.mark.integration

MOMENT = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)


def make_instrument(
    symbol: str,
    *,
    name: str = "Empresa S.A.",
    asset_class: AssetClass = AssetClass.EQUITY,
    mic: str | None = None,
    isin: str | None = None,
    cfi: str | None = None,
) -> Instrument:
    return Instrument.register(
        symbol=TickerSymbol(symbol),
        name=name,
        asset_class=asset_class,
        currency=BRL,
        mic=Mic(mic) if mic else None,
        isin=Isin(isin) if isin else None,
        cfi=CfiCode(cfi) if cfi else None,
        clock=FrozenClock(MOMENT),
    )


class TestInstrumentRepository:
    async def test_add_and_get_roundtrip(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyInstrumentRepository(db_session)
        instrument = make_instrument(
            "PETR4",
            name="Petrobras PN",
            mic="BVMF",
            isin="BRPETRACNPR6",
            cfi="ESVUFR",
        )
        await repository.add(instrument)

        loaded = await repository.get(instrument.id)
        assert loaded is not None
        assert loaded.symbol == TickerSymbol("PETR4")
        assert loaded.name == "Petrobras PN"
        assert loaded.asset_class is AssetClass.EQUITY
        assert loaded.currency.code == "BRL"
        assert loaded.mic == Mic("BVMF")
        assert loaded.isin == Isin("BRPETRACNPR6")
        assert loaded.cfi == CfiCode("ESVUFR")
        assert loaded.is_active is True
        assert loaded.created_at == instrument.created_at

        by_symbol = await repository.get_by_symbol("  petr4 ")
        assert by_symbol is not None
        assert by_symbol.id == instrument.id

    async def test_get_unknown_returns_none(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyInstrumentRepository(db_session)
        assert await repository.get(uuid4()) is None
        assert await repository.get_by_symbol("NAOEXISTE") is None

    async def test_duplicate_symbol_is_rejected(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyInstrumentRepository(db_session)
        await repository.add(make_instrument("PETR4"))
        with pytest.raises(IntegrityError):
            await repository.add(make_instrument("PETR4", name="Outra Empresa"))
        await db_session.rollback()

    async def test_duplicate_isin_is_rejected(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyInstrumentRepository(db_session)
        await repository.add(make_instrument("PETR4", isin="BRPETRACNPR6"))
        with pytest.raises(IntegrityError):
            await repository.add(make_instrument("VALE3", name="Vale S.A.", isin="BRPETRACNPR6"))
        await db_session.rollback()

    async def test_update_persists_changes(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyInstrumentRepository(db_session)
        instrument = make_instrument("PETR4")
        await repository.add(instrument)

        clock = FrozenClock(MOMENT)
        instrument.rename("Petrobras Renomeada", clock=clock)
        instrument.deactivate(clock=clock)
        await repository.update(instrument)

        loaded = await repository.get(instrument.id)
        assert loaded is not None
        assert loaded.name == "Petrobras Renomeada"
        assert loaded.is_active is False

    async def test_update_missing_instrument_raises(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyInstrumentRepository(db_session)
        with pytest.raises(NotFoundError):
            await repository.update(make_instrument("PETR4"))

    async def test_cursor_pagination_walks_the_catalogue(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyInstrumentRepository(db_session)
        for symbol in ("ABCD3", "EFGH4", "PETR4", "VALE3", "XPTO3"):
            await repository.add(make_instrument(symbol))

        first, has_more = await repository.list_page(
            limit=2, cursor=None, query=None, asset_class=None
        )
        assert [item.symbol.value for item in first] == ["ABCD3", "EFGH4"]
        assert has_more is True

        cursor = encode_cursor({"symbol": first[-1].symbol.value})
        second, has_more = await repository.list_page(
            limit=2, cursor=cursor, query=None, asset_class=None
        )
        assert [item.symbol.value for item in second] == ["PETR4", "VALE3"]
        assert has_more is True

        cursor = encode_cursor({"symbol": second[-1].symbol.value})
        third, has_more = await repository.list_page(
            limit=2, cursor=cursor, query=None, asset_class=None
        )
        assert [item.symbol.value for item in third] == ["XPTO3"]
        assert has_more is False

    async def test_list_page_filters_by_query_and_asset_class(
        self, db_session: AsyncSession
    ) -> None:
        repository = SqlAlchemyInstrumentRepository(db_session)
        await repository.add(make_instrument("PETR4", name="Petrobras PN"))
        await repository.add(make_instrument("VALE3", name="Vale S.A."))
        await repository.add(make_instrument("BTC", name="Bitcoin", asset_class=AssetClass.CRYPTO))

        by_query, _ = await repository.list_page(
            limit=10, cursor=None, query="vale", asset_class=None
        )
        assert [item.symbol.value for item in by_query] == ["VALE3"]

        by_class, _ = await repository.list_page(
            limit=10, cursor=None, query=None, asset_class=AssetClass.CRYPTO
        )
        assert [item.symbol.value for item in by_class] == ["BTC"]

    async def test_list_active_symbols_skips_inactive(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyInstrumentRepository(db_session)
        active = make_instrument("PETR4")
        inactive = make_instrument("VALE3")
        await repository.add(active)
        await repository.add(inactive)
        inactive.deactivate(clock=FrozenClock(MOMENT))
        await repository.update(inactive)

        assert await repository.list_active_symbols() == ["PETR4"]


class TestInstrumentCatalog:
    async def test_returns_summary_by_symbol(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyInstrumentRepository(db_session)
        await repository.add(make_instrument("PETR4", name="Petrobras PN"))
        catalog = SqlAlchemyInstrumentCatalog(db_session)

        summary = await catalog.get_by_symbol("petr4")
        assert summary is not None
        assert summary.symbol == "PETR4"
        assert summary.name == "Petrobras PN"
        assert summary.currency.code == "BRL"

    async def test_unknown_symbol_returns_none(self, db_session: AsyncSession) -> None:
        catalog = SqlAlchemyInstrumentCatalog(db_session)
        assert await catalog.get_by_symbol("NAOEXISTE") is None

    async def test_require_by_symbol_raises_not_found(self, db_session: AsyncSession) -> None:
        catalog = SqlAlchemyInstrumentCatalog(db_session)
        with pytest.raises(NotFoundError):
            await catalog.require_by_symbol("NAOEXISTE")
