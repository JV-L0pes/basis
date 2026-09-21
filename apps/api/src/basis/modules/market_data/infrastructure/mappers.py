"""Mapping between persistence rows and domain objects (market data)."""

from __future__ import annotations

from basis.kernel.domain.assets import AssetClass
from basis.kernel.domain.currency import Currency
from basis.modules.market_data.domain.models import Instrument
from basis.modules.market_data.domain.value_objects import CfiCode, Isin, Mic, TickerSymbol
from basis.modules.market_data.infrastructure.models import InstrumentRow


def instrument_to_domain(row: InstrumentRow) -> Instrument:
    return Instrument(
        id=row.id,
        symbol=TickerSymbol(row.symbol),
        name=row.name,
        asset_class=AssetClass(row.asset_class),
        currency=Currency.of(row.currency),
        mic=Mic(row.mic) if row.mic else None,
        isin=Isin(row.isin) if row.isin else None,
        cfi=CfiCode(row.cfi) if row.cfi else None,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def instrument_to_row(instrument: Instrument) -> InstrumentRow:
    return InstrumentRow(
        id=instrument.id,
        symbol=str(instrument.symbol),
        name=instrument.name,
        asset_class=str(instrument.asset_class),
        currency=instrument.currency.code,
        mic=str(instrument.mic) if instrument.mic else None,
        isin=str(instrument.isin) if instrument.isin else None,
        cfi=str(instrument.cfi) if instrument.cfi else None,
        is_active=instrument.is_active,
        created_at=instrument.created_at,
        updated_at=instrument.updated_at,
    )


def apply_instrument(instrument: Instrument, row: InstrumentRow) -> None:
    row.name = instrument.name
    row.asset_class = str(instrument.asset_class)
    row.currency = instrument.currency.code
    row.mic = str(instrument.mic) if instrument.mic else None
    row.isin = str(instrument.isin) if instrument.isin else None
    row.cfi = str(instrument.cfi) if instrument.cfi else None
    row.is_active = instrument.is_active
    row.updated_at = instrument.updated_at


__all__ = ["apply_instrument", "instrument_to_domain", "instrument_to_row"]
