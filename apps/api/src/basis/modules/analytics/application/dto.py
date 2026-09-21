"""Read models (DTOs) for the analytics context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EquityPointDTO:
    date: date
    value: Decimal


@dataclass(frozen=True, slots=True)
class PerformanceReport:
    """Absolute and relative performance of one portfolio over a period."""

    portfolio_id: UUID
    currency: str
    start: date
    end: date
    initial_value: Decimal
    final_value: Decimal
    net_contributions: Decimal
    twr: Decimal | None
    xirr: Decimal | None
    volatility: Decimal | None
    annualized_return: Decimal | None
    max_drawdown: Decimal
    sharpe: Decimal | None
    beta: Decimal | None
    var_95: Decimal | None
    benchmark_symbol: str | None = None
    benchmark_return: Decimal | None = None
    risk_free_annual: Decimal | None = None
    equity_curve: tuple[EquityPointDTO, ...] = ()


@dataclass(frozen=True, slots=True)
class ExposureDTO:
    asset_class: str
    value: Decimal
    weight: Decimal


@dataclass(frozen=True, slots=True)
class DriftDTO:
    asset_class: str
    current_value: Decimal
    target_value: Decimal
    current_weight: Decimal
    target_weight: Decimal
    delta_value: Decimal
    drift_bps: int


@dataclass(frozen=True, slots=True)
class RebalanceTradeDTO:
    asset_class: str
    action: str
    amount: Decimal
    drift_bps: int


@dataclass(frozen=True, slots=True)
class AllocationAnalysis:
    """Current allocation, drift against the targets and a rebalancing plan."""

    portfolio_id: UUID
    currency: str
    total_value: Decimal
    exposures: tuple[ExposureDTO, ...] = ()
    drift: tuple[DriftDTO, ...] = ()
    plan: tuple[RebalanceTradeDTO, ...] = ()
    unpriced_symbols: tuple[str, ...] = ()
    has_targets: bool = False


@dataclass(frozen=True, slots=True)
class BookOverview:
    """Aggregated view of every portfolio in the book."""

    portfolio_count: int
    total_market_value: Decimal
    allocation: tuple[ExposureDTO, ...] = field(default_factory=tuple)
    currency: str = "BRL"


__all__ = [
    "AllocationAnalysis",
    "BookOverview",
    "DriftDTO",
    "EquityPointDTO",
    "ExposureDTO",
    "PerformanceReport",
    "RebalanceTradeDTO",
]
