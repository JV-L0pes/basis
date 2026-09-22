"""Analytics use cases: performance, risk and allocation analysis."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from basis.kernel.domain.clock import Clock
from basis.kernel.domain.errors import NotFoundError, ValidationError
from basis.modules.analytics.application.dto import (
    AllocationAnalysis,
    BookOverview,
    DriftDTO,
    EquityPointDTO,
    ExposureDTO,
    PerformanceReport,
    RebalanceTradeDTO,
)
from basis.modules.analytics.application.valuation import build_valuation_series, cash_flows
from basis.modules.analytics.domain.allocation import (
    AllocationTarget,
    PricedPosition,
    allocation_drift,
    exposures_by_class,
    rebalance_plan,
)
from basis.modules.analytics.domain.performance import (
    TRADING_DAYS_PER_YEAR,
    annualized_return,
    annualized_volatility,
    beta,
    daily_returns,
    historical_var,
    max_drawdown,
    money_weighted_return,
    sharpe_ratio,
    time_weighted_return,
)
from basis.modules.market_data.domain.ports import MacroProvider, QuoteProvider
from basis.modules.market_data.domain.value_objects import MacroSeriesCode
from basis.modules.portfolio.domain.ports import PortfolioReader, PortfolioSnapshot

DEFAULT_PERIOD_DAYS = 365
DEFAULT_BENCHMARK = "^BVSP"
DEFAULT_MIN_TRADE_AMOUNT = Decimal("100.00")
ONE = Decimal(1)


class GetPortfolioPerformance:
    """Time-weighted and money-weighted performance plus risk metrics."""

    def __init__(
        self,
        *,
        portfolios: PortfolioReader,
        quotes: QuoteProvider,
        macro: MacroProvider,
        clock: Clock,
        benchmark_symbol: str = DEFAULT_BENCHMARK,
    ) -> None:
        self._portfolios = portfolios
        self._quotes = quotes
        self._macro = macro
        self._clock = clock
        self._benchmark = benchmark_symbol

    async def execute(
        self, portfolio_id: UUID, *, start: date | None = None, end: date | None = None
    ) -> PerformanceReport:
        snapshot = await self._portfolios.get_snapshot(portfolio_id)
        if snapshot is None:
            raise NotFoundError("Portfolio not found", details={"portfolio_id": str(portfolio_id)})

        resolved_end = end or self._clock.today()
        resolved_start = start or _default_start(snapshot, resolved_end)
        if resolved_end < resolved_start:
            raise ValidationError("End date must not precede start date")

        history = await self._history_for(snapshot, resolved_start, resolved_end)
        series = build_valuation_series(snapshot, history, start=resolved_start, end=resolved_end)
        if not series:
            raise ValidationError("No valuation data for the requested period")

        returns = daily_returns(series)
        values = [point.market_value for point in series]
        risk_free = await self._risk_free_annual()
        benchmark_returns, benchmark_return = await self._benchmark_series(
            resolved_start, resolved_end
        )

        flows = cash_flows(snapshot, series)
        contributions = sum((-flow.amount for flow in flows[:-1] if flow.amount < 0), Decimal(0))

        return PerformanceReport(
            portfolio_id=portfolio_id,
            currency=snapshot.base_currency,
            start=series[0].date,
            end=series[-1].date,
            initial_value=series[0].market_value,
            final_value=series[-1].market_value,
            net_contributions=contributions.quantize(Decimal("0.01")),
            twr=time_weighted_return(series),
            xirr=money_weighted_return(flows),
            volatility=annualized_volatility(returns),
            annualized_return=annualized_return(returns),
            max_drawdown=max_drawdown(values),
            sharpe=sharpe_ratio(returns, risk_free_annual=risk_free) if risk_free else None,
            beta=beta(returns, benchmark_returns) if benchmark_returns else None,
            var_95=historical_var(returns),
            benchmark_symbol=self._benchmark if benchmark_return is not None else None,
            benchmark_return=benchmark_return,
            risk_free_annual=risk_free,
            equity_curve=tuple(
                EquityPointDTO(date=point.date, value=point.market_value) for point in series
            ),
        )

    async def _history_for(
        self, snapshot: PortfolioSnapshot, start: date, end: date
    ) -> dict[str, dict[date, Decimal]]:
        symbols = [position.symbol for position in snapshot.positions]
        if not symbols:
            return {}
        series = await asyncio.gather(
            *(self._quotes.get_history(symbol, start=start, end=end) for symbol in symbols)
        )
        return {
            symbol: {point.date: point.close.amount for point in points}
            for symbol, points in zip(symbols, series, strict=True)
        }

    async def _risk_free_annual(self) -> Decimal | None:
        try:
            latest = await self._macro.latest(MacroSeriesCode.SELIC)
        except Exception:  # noqa: BLE001 — metrics must survive a missing macro series
            return None
        if latest is None:
            return None
        daily = latest.value / Decimal(100)
        return ((ONE + daily) ** TRADING_DAYS_PER_YEAR - ONE).quantize(Decimal("0.0001"))

    async def _benchmark_series(
        self, start: date, end: date
    ) -> tuple[list[Decimal], Decimal | None]:
        try:
            points = await self._quotes.get_history(self._benchmark, start=start, end=end)
        except Exception:  # noqa: BLE001 — the benchmark is optional
            return [], None
        if len(points) < 2:
            return [], None
        closes = [point.close.amount for point in points]
        returns = [closes[index] / closes[index - 1] - ONE for index in range(1, len(closes))]
        total = (closes[-1] / closes[0] - ONE).quantize(Decimal("0.0001"))
        return returns, total


class GetAllocationAnalysis:
    """Current allocation, drift against targets and a rebalancing plan."""

    def __init__(
        self,
        *,
        portfolios: PortfolioReader,
        quotes: QuoteProvider,
        min_trade_amount: Decimal = DEFAULT_MIN_TRADE_AMOUNT,
    ) -> None:
        self._portfolios = portfolios
        self._quotes = quotes
        self._min_trade_amount = min_trade_amount

    async def execute(self, portfolio_id: UUID) -> AllocationAnalysis:
        snapshot = await self._portfolios.get_snapshot(portfolio_id)
        if snapshot is None:
            raise NotFoundError("Portfolio not found", details={"portfolio_id": str(portfolio_id)})

        prices = await self._prices(snapshot)
        unpriced = tuple(
            sorted(
                position.symbol for position in snapshot.positions if position.symbol not in prices
            )
        )
        priced = [
            PricedPosition(
                symbol=position.symbol,
                asset_class=position.asset_class,
                quantity=position.quantity,
                price=prices[position.symbol],
            )
            for position in snapshot.positions
            if position.symbol in prices
        ]
        exposures = exposures_by_class(priced)
        total_value = sum((exposure.value for exposure in exposures), Decimal(0))

        targets = [
            AllocationTarget(asset_class=target.asset_class, weight_bps=target.weight_bps)
            for target in snapshot.targets
        ]
        drift_items = allocation_drift(exposures, targets, total_value=total_value)
        plan = rebalance_plan(drift_items, min_trade_amount=self._min_trade_amount)

        return AllocationAnalysis(
            portfolio_id=portfolio_id,
            currency=snapshot.base_currency,
            total_value=total_value.quantize(Decimal("0.01")),
            exposures=tuple(
                ExposureDTO(
                    asset_class=exposure.asset_class,
                    value=exposure.value.quantize(Decimal("0.01")),
                    weight=exposure.weight,
                )
                for exposure in exposures
            ),
            drift=tuple(
                DriftDTO(
                    asset_class=item.asset_class,
                    current_value=item.current_value,
                    target_value=item.target_value,
                    current_weight=item.current_weight,
                    target_weight=item.target_weight,
                    delta_value=item.delta_value,
                    drift_bps=item.drift_bps,
                )
                for item in drift_items
            ),
            plan=tuple(
                RebalanceTradeDTO(
                    asset_class=trade.asset_class,
                    action=trade.action,
                    amount=trade.amount,
                    drift_bps=trade.drift_bps,
                )
                for trade in plan
            ),
            unpriced_symbols=unpriced,
            has_targets=bool(snapshot.targets),
        )

    async def _prices(self, snapshot: PortfolioSnapshot) -> dict[str, Decimal]:
        symbols = [position.symbol for position in snapshot.positions]
        if not symbols:
            return {}
        quotes = await self._quotes.get_quotes(symbols)
        return {symbol: quote.price.amount for symbol, quote in quotes.items()}


class GetBookOverview:
    """Aggregate every portfolio: count, market value and allocation by class."""

    def __init__(
        self, *, portfolios: PortfolioReader, quotes: QuoteProvider, limit: int = 200
    ) -> None:
        self._portfolios = portfolios
        self._quotes = quotes
        self._limit = limit

    async def execute(self) -> BookOverview:
        snapshots = await self._portfolios.list_snapshots(limit=self._limit)
        if not snapshots:
            return BookOverview(portfolio_count=0, total_market_value=Decimal(0))

        symbols = {position.symbol for snapshot in snapshots for position in snapshot.positions}
        quotes = await self._quotes.get_quotes(sorted(symbols)) if symbols else {}
        prices = {symbol: quote.price.amount for symbol, quote in quotes.items()}

        values: dict[str, Decimal] = defaultdict(Decimal)
        total = Decimal(0)
        for snapshot in snapshots:
            for position in snapshot.positions:
                price = prices.get(position.symbol)
                if price is None:
                    continue
                value = position.quantity * price
                values[position.asset_class] += value
                total += value

        allocation = tuple(
            ExposureDTO(
                asset_class=asset_class,
                value=value.quantize(Decimal("0.01")),
                weight=(value / total).quantize(Decimal("0.0001")) if total > 0 else Decimal(0),
            )
            for asset_class, value in sorted(values.items())
        )
        return BookOverview(
            portfolio_count=len(snapshots),
            total_market_value=total.quantize(Decimal("0.01")),
            allocation=allocation,
        )


def _default_start(snapshot: PortfolioSnapshot, end: date) -> date:
    if snapshot.transactions:
        first = min(transaction.trade_date for transaction in snapshot.transactions)
        return min(first, end)
    return end - timedelta(days=DEFAULT_PERIOD_DAYS)


__all__ = ["GetAllocationAnalysis", "GetBookOverview", "GetPortfolioPerformance"]
