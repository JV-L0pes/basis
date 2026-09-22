"""Market data ports — the contracts other bounded contexts depend on."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from basis.kernel.domain.assets import AssetClass
from basis.kernel.domain.currency import Currency
from basis.kernel.domain.money import Money
from basis.modules.market_data.domain.models import Instrument, PricePoint
from basis.modules.market_data.domain.value_objects import MacroSeriesCode


@dataclass(frozen=True, slots=True)
class InstrumentSummary:
    """Minimal instrument data other contexts are allowed to see."""

    id: UUID
    symbol: str
    name: str
    asset_class: AssetClass
    currency: Currency


@dataclass(frozen=True, slots=True)
class QuoteView:
    """A quote projected for consumers outside this context."""

    symbol: str
    price: Money
    as_of: datetime
    source: str
    change_percent: Decimal | None = None


@dataclass(frozen=True, slots=True)
class IndexPointView:
    """A macro series observation projected for consumers."""

    code: str
    date: date
    value: Decimal


class InstrumentRepository(Protocol):
    """Persistence port for the instrument catalog."""

    async def get(self, instrument_id: UUID) -> Instrument | None: ...

    async def get_by_symbol(self, symbol: str) -> Instrument | None: ...

    async def add(self, instrument: Instrument) -> None: ...

    async def update(self, instrument: Instrument) -> None: ...

    async def list_page(
        self,
        *,
        limit: int,
        cursor: str | None = None,
        query: str | None = None,
        asset_class: AssetClass | None = None,
    ) -> tuple[Sequence[Instrument], bool]: ...

    async def list_active_symbols(self) -> Sequence[str]: ...

    async def count(self) -> int: ...


class InstrumentCatalog(Protocol):
    """Published contract: instrument lookups by symbol."""

    async def get_by_symbol(self, symbol: str) -> InstrumentSummary | None: ...

    async def require_by_symbol(self, symbol: str) -> InstrumentSummary: ...


class QuoteProvider(Protocol):
    """Published contract: price data, possibly remote and cached."""

    async def get_quote(self, symbol: str) -> QuoteView | None: ...

    async def get_quotes(self, symbols: Sequence[str]) -> Mapping[str, QuoteView]: ...

    async def get_history(self, symbol: str, *, start: date, end: date) -> Sequence[PricePoint]: ...


class MacroProvider(Protocol):
    """Published contract: macro series data."""

    async def get_series(
        self, code: MacroSeriesCode, *, start: date, end: date
    ) -> Sequence[IndexPointView]: ...

    async def latest(self, code: MacroSeriesCode) -> IndexPointView | None: ...


__all__ = [
    "IndexPointView",
    "InstrumentCatalog",
    "InstrumentRepository",
    "InstrumentSummary",
    "MacroProvider",
    "QuoteProvider",
    "QuoteView",
]
