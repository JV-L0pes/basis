"""Portfolio value objects: instrument references, transaction kinds and targets."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from basis.kernel.domain.assets import AssetClass
from basis.kernel.domain.currency import Currency
from basis.kernel.domain.errors import ValidationError

BASIS_POINTS_TOTAL = 10_000
MIN_TARGET_BPS = 0
MAX_TARGET_BPS = BASIS_POINTS_TOTAL


class TransactionKind(StrEnum):
    """Types of movements a portfolio can record."""

    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    FEE = "fee"

    @property
    def increases_quantity(self) -> bool:
        return self is TransactionKind.BUY

    @property
    def decreases_quantity(self) -> bool:
        return self is TransactionKind.SELL

    @property
    def is_cash_income(self) -> bool:
        return self in (TransactionKind.DIVIDEND, TransactionKind.INTEREST)

    @property
    def is_cash_expense(self) -> bool:
        return self is TransactionKind.FEE


class PortfolioStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class InstrumentRef:
    """The portfolio's own snapshot of the instrument it trades.

    The portfolio context never imports the market data context: it stores the
    identifier plus the classification and currency that were valid at the time
    of the first trade.
    """

    instrument_id: UUID
    symbol: str
    asset_class: AssetClass
    currency: Currency

    def __post_init__(self) -> None:
        normalized = self.symbol.strip().upper()
        if not normalized:
            raise ValidationError("Instrument symbol must not be empty")
        object.__setattr__(self, "symbol", normalized)

    def __str__(self) -> str:
        return self.symbol


@dataclass(frozen=True, slots=True)
class TargetAllocation:
    """Desired weight for an asset class, expressed in basis points."""

    asset_class: AssetClass
    weight_bps: int

    def __post_init__(self) -> None:
        if not MIN_TARGET_BPS <= self.weight_bps <= MAX_TARGET_BPS:
            raise ValidationError(
                "Target weight must be between 0 and 10000 basis points",
                details={"weight_bps": self.weight_bps},
            )

    @property
    def weight(self) -> Decimal:
        return Decimal(self.weight_bps) / Decimal(BASIS_POINTS_TOTAL)

    @property
    def percent(self) -> Decimal:
        return Decimal(self.weight_bps) / Decimal(100)


class AllocationTargets:
    """The full set of target weights. Either empty or summing to exactly 100%."""

    __slots__ = ("_targets",)

    def __init__(self, targets: Sequence[TargetAllocation]) -> None:
        materialized = tuple(sorted(targets, key=lambda target: str(target.asset_class)))
        classes = [target.asset_class for target in materialized]
        if len(set(classes)) != len(classes):
            raise ValidationError("Each asset class may appear only once in the targets")
        total = sum(target.weight_bps for target in materialized)
        if materialized and total != BASIS_POINTS_TOTAL:
            raise ValidationError(
                "Target weights must sum to 10000 basis points",
                details={"total_bps": total},
            )
        self._targets = materialized

    @classmethod
    def empty(cls) -> AllocationTargets:
        return cls(())

    @property
    def targets(self) -> tuple[TargetAllocation, ...]:
        return self._targets

    @property
    def is_empty(self) -> bool:
        return not self._targets

    def weight_of(self, asset_class: AssetClass) -> Decimal:
        for target in self._targets:
            if target.asset_class is asset_class:
                return target.weight
        return Decimal(0)

    def __iter__(self) -> Iterator[TargetAllocation]:
        return iter(self._targets)

    def __len__(self) -> int:
        return len(self._targets)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AllocationTargets):
            return NotImplemented
        return self._targets == other._targets

    def __hash__(self) -> int:
        return hash(self._targets)

    def __repr__(self) -> str:
        return f"AllocationTargets({self._targets!r})"


__all__ = [
    "BASIS_POINTS_TOTAL",
    "MAX_TARGET_BPS",
    "MIN_TARGET_BPS",
    "AllocationTargets",
    "InstrumentRef",
    "PortfolioStatus",
    "TargetAllocation",
    "TransactionKind",
]
