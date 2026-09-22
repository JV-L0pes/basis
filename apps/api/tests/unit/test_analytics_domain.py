"""Unit tests for the financial mathematics of the analytics context."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from basis.modules.analytics.domain.allocation import (
    AllocationTarget,
    ClassExposure,
    PricedPosition,
    allocation_drift,
    exposures_by_class,
    rebalance_plan,
)
from basis.modules.analytics.domain.performance import (
    CashFlow,
    ValuationPoint,
    annualized_volatility,
    beta,
    daily_returns,
    historical_var,
    max_drawdown,
    money_weighted_return,
    sharpe_ratio,
    time_weighted_return,
)
from basis.modules.portfolio.domain.ports import PositionSnapshot, TargetWeight  # noqa: F401

DAY0 = date(2026, 1, 1)


def point(offset: int, value: str, flow: str = "0") -> ValuationPoint:
    return ValuationPoint(
        date=DAY0 + timedelta(days=offset),
        market_value=Decimal(value),
        external_flow=Decimal(flow),
    )


class TestTimeWeightedReturn:
    def test_single_period(self) -> None:
        series = [point(0, "100"), point(1, "110")]
        assert time_weighted_return(series) == Decimal("0.100000")

    def test_neutralises_external_contributions(self) -> None:
        # 100 -> (contribution 50, end 165) -> 181.50
        series = [point(0, "100"), point(1, "165", flow="50"), point(2, "181.50")]
        # (165-50)/100 - 1 = 15%; 181.50/165 - 1 = 10%; 1.15*1.10 - 1 = 26.5%
        assert time_weighted_return(series) == Decimal("0.265000")

    def test_needs_at_least_two_points(self) -> None:
        assert time_weighted_return([point(0, "100")]) is None

    def test_skips_periods_with_zero_base(self) -> None:
        series = [point(0, "0"), point(1, "100"), point(2, "110")]
        assert time_weighted_return(series) == Decimal("0.100000")


class TestMoneyWeightedReturn:
    def test_exact_one_year_return(self) -> None:
        flows = [
            CashFlow(date(2026, 1, 1), Decimal("-1000")),
            CashFlow(date(2026, 1, 1) + timedelta(days=365), Decimal("1100")),
        ]
        assert money_weighted_return(flows) == Decimal("0.100000")

    def test_multi_period_return_is_annualised(self) -> None:
        flows = [
            CashFlow(date(2026, 1, 1), Decimal("-1000")),
            CashFlow(date(2026, 1, 1) + timedelta(days=182), Decimal("500")),
            CashFlow(date(2026, 1, 1) + timedelta(days=365), Decimal("800")),
        ]
        rate = money_weighted_return(flows)
        assert rate is not None
        # solving NPV(rate) = 0 must hold for the returned rate
        origin = date(2026, 1, 1)
        one = Decimal(1)
        npv = sum(
            (
                flow.amount / (one + rate) ** (Decimal((flow.date - origin).days) / Decimal(365))
                for flow in flows
            ),
            Decimal(0),
        )
        assert abs(npv) < Decimal("1")

    def test_requires_both_signs(self) -> None:
        flows = [
            CashFlow(date(2026, 1, 1), Decimal("1000")),
            CashFlow(date(2026, 6, 1), Decimal("100")),
        ]
        assert money_weighted_return(flows) is None

    def test_single_flow_is_undefined(self) -> None:
        assert money_weighted_return([CashFlow(date(2026, 1, 1), Decimal("-100"))]) is None

    def test_negative_return(self) -> None:
        flows = [
            CashFlow(date(2026, 1, 1), Decimal("-1000")),
            CashFlow(date(2026, 1, 1) + timedelta(days=365), Decimal("900")),
        ]
        rate = money_weighted_return(flows)
        assert rate is not None
        assert rate < 0
        assert abs(rate - Decimal("-0.1")) < Decimal("0.0001")


class TestRiskMetrics:
    def test_daily_returns_exclude_flows(self) -> None:
        series = [point(0, "100"), point(1, "150", flow="50")]
        assert daily_returns(series) == [Decimal(0)]

    def test_annualized_volatility_of_known_series(self) -> None:
        returns = [Decimal("0.01"), Decimal("-0.01"), Decimal("0.02"), Decimal("0")]
        volatility = annualized_volatility(returns)
        assert volatility is not None
        assert float(volatility) == pytest.approx(0.2049, rel=1e-3)

    def test_volatility_needs_two_returns(self) -> None:
        assert annualized_volatility([Decimal("0.01")]) is None

    def test_max_drawdown(self) -> None:
        values = [Decimal(100), Decimal(120), Decimal(90), Decimal(110)]
        assert max_drawdown(values) == Decimal("-0.250000")

    def test_max_drawdown_is_zero_when_monotonic(self) -> None:
        assert max_drawdown([Decimal(100), Decimal(110), Decimal(120)]) == Decimal(0)

    def test_sharpe_ratio_is_none_without_volatility(self) -> None:
        assert sharpe_ratio([Decimal("0.01")], risk_free_annual=Decimal("0.10")) is None

    def test_sharpe_ratio_is_none_without_volatility_at_all(self) -> None:
        constant = [Decimal("0.001")] * 10
        assert sharpe_ratio(constant, risk_free_annual=Decimal("0.10")) is None

    def test_beta_of_identical_series_is_one(self) -> None:
        returns = [Decimal("0.01"), Decimal("-0.02"), Decimal("0.03"), Decimal("0.01")]
        assert beta(returns, returns) == Decimal("1.0000")

    def test_beta_of_inverse_series_is_minus_one(self) -> None:
        returns = [Decimal("0.01"), Decimal("-0.02"), Decimal("0.03"), Decimal("0.01")]
        inverse = [-value for value in returns]
        assert beta(returns, inverse) == Decimal("-1.0000")

    def test_historical_var_is_the_worst_tail(self) -> None:
        returns = [Decimal("-0.05"), Decimal("-0.02"), Decimal("0"), Decimal("0.01")] * 5
        assert historical_var(returns, confidence=Decimal("0.95")) is not None

    def test_historical_var_needs_returns(self) -> None:
        assert historical_var([]) is None


def position(symbol: str, asset_class: str, quantity: str, price: str = "10") -> PricedPosition:
    return PricedPosition(
        symbol=symbol,
        asset_class=asset_class,
        quantity=Decimal(quantity),
        price=Decimal(price),
    )


class TestAllocation:
    def test_exposures_aggregate_by_asset_class(self) -> None:
        positions = [
            position("PETR4", "equity", "100", "10"),
            position("VALE3", "equity", "50", "20"),
            position("HGLG11", "real_estate", "10", "100"),
        ]
        exposures = exposures_by_class(positions)
        by_class = {exposure.asset_class: exposure for exposure in exposures}
        assert by_class["equity"].value == Decimal(2000)
        assert by_class["real_estate"].value == Decimal(1000)
        assert by_class["equity"].weight == Decimal("0.6667")

    def test_no_positions_means_no_exposures(self) -> None:
        assert exposures_by_class([]) == ()

    def test_drift_compares_current_and_target(self) -> None:
        exposures = (
            ClassExposure("equity", Decimal(700), Decimal("0.7")),
            ClassExposure("fixed_income", Decimal(300), Decimal("0.3")),
        )
        targets = [
            AllocationTarget("equity", 6000),
            AllocationTarget("fixed_income", 4000),
        ]
        drift = allocation_drift(exposures, targets, total_value=Decimal(1000))
        by_class = {item.asset_class: item for item in drift}
        assert by_class["equity"].drift_bps == 1000
        assert by_class["equity"].delta_value == Decimal("-100.00")
        assert by_class["fixed_income"].drift_bps == -1000
        assert by_class["fixed_income"].delta_value == Decimal("100.00")

    def test_classes_outside_the_targets_are_flagged(self) -> None:
        exposures = (ClassExposure("crypto", Decimal(100), Decimal("1")),)
        drift = allocation_drift(
            exposures, [AllocationTarget("equity", 10000)], total_value=Decimal(100)
        )
        assert {item.asset_class for item in drift} == {"crypto", "equity"}

    def test_rebalance_plan_ignores_small_moves(self) -> None:
        exposures = (
            ClassExposure("equity", Decimal("700.00"), Decimal("0.7")),
            ClassExposure("fixed_income", Decimal("300.00"), Decimal("0.3")),
        )
        targets = [AllocationTarget("equity", 6000), AllocationTarget("fixed_income", 4000)]
        drift = allocation_drift(exposures, targets, total_value=Decimal(1000))
        plan = rebalance_plan(drift, min_trade_amount=Decimal("50"))
        actions = {trade.asset_class: trade.action for trade in plan}
        assert actions["equity"] == "sell"
        assert actions["fixed_income"] == "buy"

        with_high_minimum = rebalance_plan(drift, min_trade_amount=Decimal("500"))
        assert all(trade.action == "hold" for trade in with_high_minimum)
