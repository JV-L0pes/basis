"""Allocation analysis: exposures, drift against targets and rebalancing.

The functions work on the analytics context's own vocabulary (``PricedPosition``
and ``AllocationTarget``); the application layer maps portfolio snapshots into
these types, which keeps the bounded contexts independent.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

BASIS_POINTS = Decimal(10_000)


@dataclass(frozen=True, slots=True)
class PricedPosition:
    """A position marked to market, in the analytics context's terms."""

    symbol: str
    asset_class: str
    quantity: Decimal
    price: Decimal

    @property
    def value(self) -> Decimal:
        return (self.quantity * self.price).quantize(Decimal("0.01"))


@dataclass(frozen=True, slots=True)
class AllocationTarget:
    """Target weight of an asset class, in basis points."""

    asset_class: str
    weight_bps: int


@dataclass(frozen=True, slots=True)
class ClassExposure:
    """How much of the portfolio's market value sits in one asset class."""

    asset_class: str
    value: Decimal
    weight: Decimal


@dataclass(frozen=True, slots=True)
class DriftItem:
    """Difference between the current and the target weight of an asset class."""

    asset_class: str
    current_value: Decimal
    target_value: Decimal
    current_weight: Decimal
    target_weight: Decimal
    delta_value: Decimal
    drift_bps: int

    @property
    def is_balanced(self) -> bool:
        return self.drift_bps == 0


@dataclass(frozen=True, slots=True)
class RebalanceTrade:
    """Suggested trade to move one asset class back to its target."""

    asset_class: str
    action: str  # "buy" | "sell" | "hold"
    amount: Decimal
    drift_bps: int


def exposures_by_class(positions: Sequence[PricedPosition]) -> tuple[ClassExposure, ...]:
    """Aggregate market value per asset class."""
    values: dict[str, Decimal] = {}
    for position in positions:
        values[position.asset_class] = values.get(position.asset_class, Decimal(0)) + (
            position.value
        )

    total = sum(values.values(), Decimal(0))
    exposures: list[ClassExposure] = []
    for asset_class in sorted(values):
        value = values[asset_class]
        weight = (value / total).quantize(Decimal("0.0001")) if total > 0 else Decimal(0)
        exposures.append(ClassExposure(asset_class=asset_class, value=value, weight=weight))
    return tuple(exposures)


def allocation_drift(
    exposures: Sequence[ClassExposure],
    targets: Sequence[AllocationTarget],
    *,
    total_value: Decimal,
) -> tuple[DriftItem, ...]:
    """Compare current weights with the strategic targets.

    Asset classes present in the portfolio but absent from the targets are
    treated as having a 0% target, and vice versa.
    """
    current = {exposure.asset_class: exposure for exposure in exposures}
    target_by_class = {target.asset_class: target.weight_bps for target in targets}
    all_classes = sorted(set(current) | set(target_by_class))

    items: list[DriftItem] = []
    for asset_class in all_classes:
        target_bps = target_by_class.get(asset_class, 0)
        exposure = current.get(asset_class)
        current_value = exposure.value if exposure else Decimal(0)
        current_weight = (
            (current_value / total_value).quantize(Decimal("0.0001"))
            if total_value > 0
            else Decimal(0)
        )
        target_weight = Decimal(target_bps) / BASIS_POINTS
        target_value = (total_value * target_weight).quantize(Decimal("0.01"))
        items.append(
            DriftItem(
                asset_class=asset_class,
                current_value=current_value,
                target_value=target_value,
                current_weight=current_weight,
                target_weight=target_weight,
                delta_value=(target_value - current_value).quantize(Decimal("0.01")),
                drift_bps=int(
                    ((current_weight - target_weight) * BASIS_POINTS).to_integral_value()
                ),
            )
        )
    return tuple(sorted(items, key=lambda item: abs(item.drift_bps), reverse=True))


def rebalance_plan(
    drift_items: Sequence[DriftItem], *, min_trade_amount: Decimal
) -> tuple[RebalanceTrade, ...]:
    """Turn drift into concrete buy/sell suggestions.

    Classes that are underweight are bought with the proceeds of the overweight
    ones; moves smaller than ``min_trade_amount`` are ignored so the suggestion
    list stays actionable.
    """
    trades: list[RebalanceTrade] = []
    for item in drift_items:
        amount = abs(item.delta_value)
        if amount < min_trade_amount:
            trades.append(
                RebalanceTrade(
                    asset_class=item.asset_class,
                    action="hold",
                    amount=Decimal(0),
                    drift_bps=item.drift_bps,
                )
            )
            continue
        trades.append(
            RebalanceTrade(
                asset_class=item.asset_class,
                action="buy" if item.delta_value > 0 else "sell",
                amount=amount,
                drift_bps=item.drift_bps,
            )
        )
    return tuple(trades)


__all__ = [
    "AllocationTarget",
    "ClassExposure",
    "DriftItem",
    "PricedPosition",
    "RebalanceTrade",
    "allocation_drift",
    "exposures_by_class",
    "rebalance_plan",
]
