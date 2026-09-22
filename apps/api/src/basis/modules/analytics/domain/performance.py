"""Performance and risk mathematics — pure functions, no I/O.

Conventions follow market practice:

* returns are decimal fractions (``0.01`` = 1%);
* a year has 252 trading days for annualisation;
* time-weighted return (TWR) removes the effect of external cash flows;
* money-weighted return (XIRR) is the rate that zeroes the NPV of the dated
  cash flows, using an actual/365 day count.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import math

TRADING_DAYS_PER_YEAR = 252
DAYS_PER_YEAR = Decimal(365)
ZERO = Decimal(0)
ONE = Decimal(1)

DEFAULT_GUESS = Decimal("0.10")
DEFAULT_TOLERANCE = Decimal("1E-9")
MAX_NEWTON_ITERATIONS = 100
BISECTION_ITERATIONS = 200


@dataclass(frozen=True, slots=True)
class ValuationPoint:
    """A day in the portfolio's history.

    ``external_flow`` is the net money the investor moved in (positive) or out
    (negative) on that date; it is excluded from the return of the day.
    """

    date: date
    market_value: Decimal
    external_flow: Decimal = ZERO


@dataclass(frozen=True, slots=True)
class CashFlow:
    """A dated cash flow for money-weighted calculations."""

    date: date
    amount: Decimal


def time_weighted_return(points: Sequence[ValuationPoint]) -> Decimal | None:
    """Chain daily sub-period returns, neutralising external cash flows."""
    if len(points) < 2:
        return None
    growth = ONE
    previous: ValuationPoint | None = None
    for point in points:
        if previous is None:
            previous = point
            continue
        base = previous.market_value
        if base <= 0:
            previous = point
            continue
        period_return = (point.market_value - point.external_flow) / base - ONE
        growth *= ONE + period_return
        previous = point
    return (growth - ONE).quantize(Decimal("0.000001"))


def money_weighted_return(flows: Sequence[CashFlow]) -> Decimal | None:
    """Annualised internal rate of return of dated cash flows (XIRR)."""
    if len(flows) < 2:
        return None
    if not any(flow.amount > 0 for flow in flows) or not any(flow.amount < 0 for flow in flows):
        return None

    origin = min(flow.date for flow in flows)

    def npv(rate: Decimal) -> Decimal:
        total = ZERO
        for flow in flows:
            years = Decimal((flow.date - origin).days) / DAYS_PER_YEAR
            total += flow.amount / (ONE + rate) ** years
        return total

    rate = _newton_raphson(npv)
    if rate is not None:
        return rate
    return _bisection(npv)


def _newton_raphson(npv: Callable[[Decimal], Decimal]) -> Decimal | None:
    rate = DEFAULT_GUESS
    step = Decimal("0.000001")
    for _ in range(MAX_NEWTON_ITERATIONS):
        value = npv(rate)
        if abs(value) < DEFAULT_TOLERANCE:
            return rate.quantize(Decimal("0.000001"))
        derivative = (npv(rate + step) - value) / step
        if derivative == 0:
            return None
        candidate = rate - value / derivative
        if candidate <= Decimal("-0.9999") or candidate > Decimal(1000):
            return None
        if abs(candidate - rate) < DEFAULT_TOLERANCE:
            return candidate.quantize(Decimal("0.000001"))
        rate = candidate
    return None


def _bisection(npv: Callable[[Decimal], Decimal]) -> Decimal | None:
    low, high = Decimal("-0.9999"), Decimal(1000)
    low_value = npv(low)
    if low_value * npv(high) > 0:
        return None
    midpoint = low
    for _ in range(BISECTION_ITERATIONS):
        midpoint = (low + high) / 2
        mid_value = npv(midpoint)
        if abs(mid_value) < DEFAULT_TOLERANCE:
            break
        if low_value * mid_value < 0:
            high = midpoint
        else:
            low, low_value = midpoint, mid_value
    return midpoint.quantize(Decimal("0.000001"))


def daily_returns(points: Sequence[ValuationPoint]) -> list[Decimal]:
    """Sub-period returns from a valuation series (external flows removed)."""
    returns: list[Decimal] = []
    previous: ValuationPoint | None = None
    for point in points:
        if previous is None:
            previous = point
            continue
        if previous.market_value <= 0:
            previous = point
            continue
        returns.append((point.market_value - point.external_flow) / previous.market_value - ONE)
        previous = point
    return returns


def _mean(values: Sequence[Decimal]) -> Decimal:
    return sum(values, ZERO) / Decimal(len(values))


def _sample_stddev(values: Sequence[Decimal]) -> Decimal | None:
    if len(values) < 2:
        return None
    mean = _mean(values)
    variance = sum((value - mean) ** 2 for value in values) / Decimal(len(values) - 1)
    return variance.sqrt()


def annualized_volatility(returns: Sequence[Decimal]) -> Decimal | None:
    """Annualised sample standard deviation of periodic returns."""
    stddev = _sample_stddev(returns)
    if stddev is None:
        return None
    factor = Decimal(math.sqrt(TRADING_DAYS_PER_YEAR))
    return (stddev * factor).quantize(Decimal("0.000001"))


def annualized_return(returns: Sequence[Decimal]) -> Decimal | None:
    """Geometric annualised return of daily returns."""
    if not returns:
        return None
    growth = ONE
    for value in returns:
        growth *= ONE + value
    if growth <= 0:
        return None
    exponent = Decimal(TRADING_DAYS_PER_YEAR) / Decimal(len(returns))
    return (growth**exponent - ONE).quantize(Decimal("0.000001"))


def sharpe_ratio(returns: Sequence[Decimal], *, risk_free_annual: Decimal) -> Decimal | None:
    """Annualised excess return per unit of annualised volatility."""
    volatility = annualized_volatility(returns)
    annual = annualized_return(returns)
    if volatility is None or annual is None or volatility == 0:
        return None
    return ((annual - risk_free_annual) / volatility).quantize(Decimal("0.0001"))


def max_drawdown(values: Sequence[Decimal]) -> Decimal:
    """Largest peak-to-trough decline, as a negative fraction (or zero)."""
    peak = Decimal(0)
    worst = Decimal(0)
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            drawdown = value / peak - ONE
            worst = min(worst, drawdown)
    return worst.quantize(Decimal("0.000001"))


def beta(returns: Sequence[Decimal], benchmark: Sequence[Decimal]) -> Decimal | None:
    """Sensitivity of the portfolio returns to the benchmark returns."""
    length = min(len(returns), len(benchmark))
    if length < 2:
        return None
    sample = list(returns[-length:])
    reference = list(benchmark[-length:])
    mean_sample = _mean(sample)
    mean_reference = _mean(reference)
    covariance = sum(
        (sample[index] - mean_sample) * (reference[index] - mean_reference)
        for index in range(length)
    ) / Decimal(length - 1)
    variance = sum((value - mean_reference) ** 2 for value in reference) / Decimal(length - 1)
    if variance == 0:
        return None
    return (covariance / variance).quantize(Decimal("0.0001"))


def historical_var(
    returns: Sequence[Decimal], *, confidence: Decimal = Decimal("0.95")
) -> Decimal | None:
    """Historical value at risk: the loss at the given confidence level."""
    if not returns:
        return None
    if not (ZERO < confidence < ONE):
        return None
    ordered = sorted(returns)
    index = int((ONE - confidence) * Decimal(len(ordered)))
    index = max(0, min(index, len(ordered) - 1))
    return ordered[index].quantize(Decimal("0.000001"))


__all__ = [
    "TRADING_DAYS_PER_YEAR",
    "CashFlow",
    "ValuationPoint",
    "annualized_return",
    "annualized_volatility",
    "beta",
    "daily_returns",
    "historical_var",
    "max_drawdown",
    "money_weighted_return",
    "sharpe_ratio",
    "time_weighted_return",
]
