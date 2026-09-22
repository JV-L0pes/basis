"""Projection that turns a portfolio ledger plus price history into a value series.

This is a read-model projection owned by the analytics context: it replays the
ledger to know the quantities held on each day, then marks them to market.

Assumptions (documented because they shape every metric):

* income (dividends/interest) and fees stay in the portfolio's cash balance;
* buys are external contributions and sells are external withdrawals;
* symbols without market data are marked at cost.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from basis.modules.analytics.domain.performance import CashFlow, ValuationPoint
from basis.modules.portfolio.domain.ports import PortfolioSnapshot, TransactionSnapshot

ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class PriceSeries:
    """Sorted closes for one symbol, so lookups are O(log n) instead of O(n)."""

    dates: tuple[date, ...]
    closes: tuple[Decimal, ...]

    @classmethod
    def from_map(cls, series: Mapping[date, Decimal]) -> PriceSeries:
        ordered = sorted(series.items())
        return cls(
            dates=tuple(moment for moment, _ in ordered),
            closes=tuple(close for _, close in ordered),
        )

    def close_on(self, day: date, fallback: Decimal | None) -> Decimal:
        """Last known close on or before ``day``; cost is the final fallback."""
        index = bisect_right(self.dates, day)
        if index == 0:
            return fallback if fallback is not None else ZERO
        return self.closes[index - 1]


def build_valuation_series(
    snapshot: PortfolioSnapshot,
    history: Mapping[str, Mapping[date, Decimal]],
    *,
    start: date,
    end: date,
) -> list[ValuationPoint]:
    """Return the daily value of the portfolio between ``start`` and ``end``."""
    if end < start:
        return []

    fallback = {position.symbol: position.average_cost for position in snapshot.positions}
    series = {
        symbol: PriceSeries.from_map(points)
        for symbol, points in history.items()
    }
    by_day: dict[date, list[TransactionSnapshot]] = defaultdict(list)
    for transaction in sorted(snapshot.transactions, key=lambda item: item.trade_date):
        by_day[transaction.trade_date].append(transaction)

    quantities: dict[str, Decimal] = defaultdict(Decimal)
    cash = ZERO
    points: list[ValuationPoint] = []

    day = start
    while day <= end:
        external_flow = ZERO
        for transaction in by_day.get(day, []):
            gross = transaction.quantity * transaction.price
            if transaction.kind == "buy":
                quantities[transaction.symbol] += transaction.quantity
                external_flow += gross + transaction.fees
            elif transaction.kind == "sell":
                quantities[transaction.symbol] -= transaction.quantity
                external_flow -= gross - transaction.fees
            elif transaction.kind in ("dividend", "interest"):
                cash += gross - transaction.fees
            else:  # fee
                cash -= gross + transaction.fees

        market_value = ZERO
        for symbol, quantity in quantities.items():
            if quantity <= 0:
                continue
            prices = series.get(symbol) or PriceSeries.from_map({})
            price = prices.close_on(day, fallback.get(symbol))
            market_value += quantity * price

        points.append(
            ValuationPoint(
                date=day,
                market_value=(market_value + cash).quantize(Decimal("0.01")),
                external_flow=external_flow.quantize(Decimal("0.01")),
            )
        )
        day += timedelta(days=1)

    return points


def cash_flows(snapshot: PortfolioSnapshot, valuation: Sequence[ValuationPoint]) -> list[CashFlow]:
    """Dated external cash flows plus the final portfolio value (for XIRR)."""
    flows: list[CashFlow] = []
    for transaction in sorted(snapshot.transactions, key=lambda item: item.trade_date):
        gross = transaction.quantity * transaction.price
        if transaction.kind == "buy":
            flows.append(CashFlow(transaction.trade_date, -(gross + transaction.fees)))
        elif transaction.kind == "sell" or transaction.kind in ("dividend", "interest"):
            flows.append(CashFlow(transaction.trade_date, gross - transaction.fees))
        else:
            flows.append(CashFlow(transaction.trade_date, -(gross + transaction.fees)))
    if valuation:
        final = valuation[-1]
        flows.append(CashFlow(final.date, final.market_value))
    return flows


__all__ = ["build_valuation_series", "cash_flows"]
