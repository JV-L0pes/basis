"""HTTP schemas for the analytics context."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from basis.modules.analytics.application.dto import (
    AllocationAnalysis,
    BookOverview,
    DriftDTO,
    EquityPointDTO,
    ExposureDTO,
    PerformanceReport,
    RebalanceTradeDTO,
)


class EquityPointResponse(BaseModel):
    date: date
    value: str

    @classmethod
    def from_dto(cls, point: EquityPointDTO) -> EquityPointResponse:
        return cls(date=point.date, value=str(point.value.quantize(Decimal("0.01"))))


class PerformanceResponse(BaseModel):
    portfolio_id: UUID
    currency: str
    start: date
    end: date
    initial_value: str
    final_value: str
    net_contributions: str
    twr: float | None
    xirr: float | None
    volatility: float | None
    annualized_return: float | None
    max_drawdown: float | None
    sharpe: float | None
    beta: float | None
    var_95: float | None
    benchmark_symbol: str | None
    benchmark_return: float | None
    risk_free_annual: float | None
    equity_curve: list[EquityPointResponse]

    @classmethod
    def from_report(cls, report: PerformanceReport) -> PerformanceResponse:
        return cls(
            portfolio_id=report.portfolio_id,
            currency=report.currency,
            start=report.start,
            end=report.end,
            initial_value=str(report.initial_value),
            final_value=str(report.final_value),
            net_contributions=str(report.net_contributions),
            twr=_to_float(report.twr),
            xirr=_to_float(report.xirr),
            volatility=_to_float(report.volatility),
            annualized_return=_to_float(report.annualized_return),
            max_drawdown=_to_float(report.max_drawdown),
            sharpe=_to_float(report.sharpe),
            beta=_to_float(report.beta),
            var_95=_to_float(report.var_95),
            benchmark_symbol=report.benchmark_symbol,
            benchmark_return=_to_float(report.benchmark_return),
            risk_free_annual=_to_float(report.risk_free_annual),
            equity_curve=[
                EquityPointResponse.from_dto(point) for point in report.equity_curve
            ],
        )


class ExposureResponse(BaseModel):
    asset_class: str
    value: str
    weight: float

    @classmethod
    def from_dto(cls, exposure: ExposureDTO) -> ExposureResponse:
        return cls(
            asset_class=exposure.asset_class,
            value=str(exposure.value),
            weight=float(exposure.weight),
        )


class DriftResponse(BaseModel):
    asset_class: str
    current_value: str
    target_value: str
    current_weight: float
    target_weight: float
    delta_value: str
    drift_bps: int

    @classmethod
    def from_dto(cls, item: DriftDTO) -> DriftResponse:
        return cls(
            asset_class=item.asset_class,
            current_value=str(item.current_value),
            target_value=str(item.target_value),
            current_weight=float(item.current_weight),
            target_weight=float(item.target_weight),
            delta_value=str(item.delta_value),
            drift_bps=item.drift_bps,
        )


class RebalanceTradeResponse(BaseModel):
    asset_class: str
    action: str
    amount: str
    drift_bps: int

    @classmethod
    def from_dto(cls, trade: RebalanceTradeDTO) -> RebalanceTradeResponse:
        return cls(
            asset_class=trade.asset_class,
            action=trade.action,
            amount=str(trade.amount),
            drift_bps=trade.drift_bps,
        )


class AllocationAnalysisResponse(BaseModel):
    portfolio_id: UUID
    currency: str
    total_value: str
    exposures: list[ExposureResponse]
    drift: list[DriftResponse]
    plan: list[RebalanceTradeResponse]
    unpriced_symbols: list[str]
    has_targets: bool

    @classmethod
    def from_analysis(cls, analysis: AllocationAnalysis) -> AllocationAnalysisResponse:
        return cls(
            portfolio_id=analysis.portfolio_id,
            currency=analysis.currency,
            total_value=str(analysis.total_value),
            exposures=[ExposureResponse.from_dto(item) for item in analysis.exposures],
            drift=[DriftResponse.from_dto(item) for item in analysis.drift],
            plan=[RebalanceTradeResponse.from_dto(item) for item in analysis.plan],
            unpriced_symbols=list(analysis.unpriced_symbols),
            has_targets=analysis.has_targets,
        )


class BookOverviewResponse(BaseModel):
    portfolio_count: int
    total_market_value: str
    allocation: list[ExposureResponse]
    currency: str

    @classmethod
    def from_overview(cls, overview: BookOverview) -> BookOverviewResponse:
        return cls(
            portfolio_count=overview.portfolio_count,
            total_market_value=str(overview.total_market_value),
            allocation=[ExposureResponse.from_dto(item) for item in overview.allocation],
            currency=overview.currency,
        )


def _to_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


__all__ = [
    "AllocationAnalysisResponse",
    "BookOverviewResponse",
    "PerformanceResponse",
]
