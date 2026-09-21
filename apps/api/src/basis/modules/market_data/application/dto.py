"""Read models (DTOs) for the market data context."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

from basis.kernel.domain.assets import AssetClass
from basis.modules.market_data.domain.models import Instrument
from basis.modules.market_data.domain.ports import IndexPointView, QuoteView


@dataclass(frozen=True, slots=True)
class InstrumentView:
    id: UUID
    symbol: str
    name: str
    asset_class: AssetClass
    currency: str
    mic: str | None
    isin: str | None
    cfi: str | None
    is_active: bool

    @classmethod
    def from_entity(cls, instrument: Instrument) -> InstrumentView:
        return cls(
            id=instrument.id,
            symbol=str(instrument.symbol),
            name=instrument.name,
            asset_class=instrument.asset_class,
            currency=instrument.currency.code,
            mic=str(instrument.mic) if instrument.mic else None,
            isin=str(instrument.isin) if instrument.isin else None,
            cfi=str(instrument.cfi) if instrument.cfi else None,
            is_active=instrument.is_active,
        )

    @classmethod
    def from_entities(cls, instruments: Iterable[Instrument]) -> list[InstrumentView]:
        return [cls.from_entity(instrument) for instrument in instruments]


@dataclass(frozen=True, slots=True)
class InstrumentPage:
    """A keyset page of instruments."""

    items: list[InstrumentView]
    next_cursor: str | None = None

    @property
    def has_more(self) -> bool:
        return self.next_cursor is not None


@dataclass(frozen=True, slots=True)
class PricePointDTO:
    date: date
    close: Decimal
    currency: str


@dataclass(frozen=True, slots=True)
class MarketOverview:
    """Dashboard snapshot: macro indicators plus the main instrument quotes."""

    macro: list[IndexPointView] = field(default_factory=list)
    quotes: list[QuoteView] = field(default_factory=list)
    gainers: list[QuoteView] = field(default_factory=list)
    losers: list[QuoteView] = field(default_factory=list)


__all__ = ["InstrumentPage", "InstrumentView", "MarketOverview", "PricePointDTO"]
