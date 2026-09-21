"""Market data domain models: instruments, quotes and series points."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from basis.kernel.domain.assets import AssetClass
from basis.kernel.domain.clock import Clock
from basis.kernel.domain.currency import Currency
from basis.kernel.domain.entity import AggregateRoot
from basis.kernel.domain.errors import ValidationError
from basis.kernel.domain.identifiers import new_id
from basis.kernel.domain.money import Money
from basis.modules.market_data.domain.events import (
    InstrumentDeactivated,
    InstrumentRegistered,
)
from basis.modules.market_data.domain.value_objects import (
    CfiCode,
    Isin,
    MacroSeriesCode,
    Mic,
    QuoteSource,
    TickerSymbol,
)

NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 120


@dataclass(eq=False, slots=True)
class Instrument(AggregateRoot[UUID]):
    """A tradable instrument in the reference catalog."""

    symbol: TickerSymbol
    name: str
    asset_class: AssetClass
    currency: Currency
    mic: Mic | None
    isin: Isin | None
    cfi: CfiCode | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def register(
        cls,
        *,
        symbol: TickerSymbol,
        name: str,
        asset_class: AssetClass,
        currency: Currency,
        mic: Mic | None = None,
        isin: Isin | None = None,
        cfi: CfiCode | None = None,
        clock: Clock,
    ) -> Instrument:
        moment = clock.now()
        instrument = cls(
            id=new_id(),
            symbol=symbol,
            name=_validate_name(name),
            asset_class=asset_class,
            currency=currency,
            mic=mic,
            isin=isin,
            cfi=cfi,
            is_active=True,
            created_at=moment,
            updated_at=moment,
        )
        instrument.record(
            InstrumentRegistered(
                occurred_at=moment,
                instrument_id=instrument.id,
                symbol=str(symbol),
                asset_class=str(asset_class),
            )
        )
        return instrument

    def rename(self, name: str, *, clock: Clock) -> None:
        self.name = _validate_name(name)
        self.updated_at = clock.now()

    def deactivate(self, *, clock: Clock) -> None:
        if not self.is_active:
            return
        moment = clock.now()
        self.is_active = False
        self.updated_at = moment
        self.record(
            InstrumentDeactivated(
                occurred_at=moment, instrument_id=self.id, symbol=str(self.symbol)
            )
        )


@dataclass(frozen=True, slots=True)
class Quote:
    """A price snapshot for an instrument."""

    instrument_id: UUID | None
    symbol: TickerSymbol
    price: Money
    as_of: datetime
    source: QuoteSource
    change_percent: Decimal | None = None

    def __post_init__(self) -> None:
        if self.as_of.tzinfo is None or self.as_of.utcoffset() != timedelta(0):
            raise ValidationError("Quote timestamp must be timezone-aware UTC")
        if self.price.is_negative():
            raise ValidationError(
                "Quote price cannot be negative", details={"price": str(self.price)}
            )

    def normalized(self) -> Quote:
        """Return the quote with ``as_of`` converted to UTC."""
        return Quote(
            instrument_id=self.instrument_id,
            symbol=self.symbol,
            price=self.price,
            as_of=self.as_of.astimezone(UTC),
            source=self.source,
            change_percent=self.change_percent,
        )


@dataclass(frozen=True, slots=True)
class PricePoint:
    """A daily close used for history and performance calculations."""

    date: date
    close: Money


@dataclass(frozen=True, slots=True)
class MacroPoint:
    """A single observation of a macro series."""

    code: MacroSeriesCode
    date: date
    value: Decimal


def _validate_name(name: str) -> str:
    normalized = " ".join(name.split())
    if not (NAME_MIN_LENGTH <= len(normalized) <= NAME_MAX_LENGTH):
        raise ValidationError(
            f"Instrument name must be between {NAME_MIN_LENGTH} and {NAME_MAX_LENGTH} characters",
            details={"length": len(normalized)},
        )
    return normalized


__all__ = ["Instrument", "MacroPoint", "PricePoint", "Quote"]
