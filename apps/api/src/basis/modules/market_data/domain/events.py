"""Market data domain events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from basis.kernel.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class InstrumentRegistered(DomainEvent):
    name: ClassVar[str] = "market_data.instrument_registered"
    instrument_id: UUID
    symbol: str
    asset_class: str


@dataclass(frozen=True, slots=True)
class InstrumentDeactivated(DomainEvent):
    name: ClassVar[str] = "market_data.instrument_deactivated"
    instrument_id: UUID
    symbol: str


__all__ = ["InstrumentDeactivated", "InstrumentRegistered"]
