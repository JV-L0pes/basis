"""Pure valuation of a portfolio against a price map."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from basis.kernel.domain.currency import Currency
from basis.kernel.domain.money import Money
from basis.modules.portfolio.domain.models import Portfolio, Position
from basis.modules.portfolio.domain.value_objects import InstrumentRef


@dataclass(frozen=True, slots=True)
class PositionValuation:
    instrument: InstrumentRef
    quantity: Decimal
    average_cost: Money
    cost_basis: Money
    market_price: Money | None
    market_value: Money | None
    unrealized_gain: Money | None
    unrealized_gain_percent: Decimal | None
    realized_gain: Money
    income: Money
    costs: Money
    weight: Decimal | None

    @property
    def net_result(self) -> Money:
        unrealized = self.unrealized_gain or Money.zero(self.instrument.currency)
        return (unrealized + self.realized_gain + self.income - self.costs).quantize()


@dataclass(frozen=True, slots=True)
class PortfolioValuation:
    """A snapshot of what the portfolio is worth and how it performed."""

    portfolio_id: UUID
    base_currency: Currency
    positions: tuple[PositionValuation, ...]
    invested: Money
    market_value: Money
    unrealized_gain: Money
    realized_gain: Money
    income: Money
    costs: Money
    unpriced_symbols: tuple[str, ...]

    @property
    def net_result(self) -> Money:
        return (self.unrealized_gain + self.realized_gain + self.income - self.costs).quantize()

    @property
    def return_percent(self) -> Decimal | None:
        if self.invested.is_zero():
            return None
        return (self.net_result.amount / self.invested.amount * 100).quantize(Decimal("0.01"))


def valuate(
    portfolio: Portfolio,
    prices: Mapping[str, Money],
    *,
    include_closed: bool = False,
) -> PortfolioValuation:
    """Build a :class:`PortfolioValuation` from the ledger and a price map.

    Symbols missing from ``prices`` are reported in ``unpriced_symbols`` and
    excluded from market-value based figures, so partial data is never silently
    treated as zero.
    """
    base = portfolio.base_currency
    positions = [
        position for position in portfolio.positions() if include_closed or position.is_open
    ]

    marked: list[tuple[Position, Money | None]] = []
    unpriced: list[str] = []
    total_market_value = Money.zero(base)
    for position in positions:
        price = prices.get(position.instrument.symbol)
        marked.append((position, price))
        if price is None:
            unpriced.append(position.instrument.symbol)
        else:
            total_market_value = total_market_value + (price * position.quantity).quantize()

    valuations: list[PositionValuation] = []
    invested = Money.zero(base)
    unrealized = Money.zero(base)
    realized = Money.zero(base)
    income = Money.zero(base)
    costs = Money.zero(base)

    for position, price in marked:
        cost_basis = position.cost_basis
        invested = invested + cost_basis
        realized = realized + position.realized_gain
        income = income + position.income
        costs = costs + position.costs

        market_value: Money | None = None
        gain: Money | None = None
        gain_percent: Decimal | None = None
        weight: Decimal | None = None
        if price is not None:
            market_value = (price * position.quantity).quantize()
            gain = (market_value - cost_basis).quantize()
            if not cost_basis.is_zero():
                gain_percent = (gain.amount / cost_basis.amount * 100).quantize(Decimal("0.01"))
            if not total_market_value.is_zero():
                weight = (market_value.amount / total_market_value.amount).quantize(
                    Decimal("0.0001")
                )
            unrealized = unrealized + gain

        valuations.append(
            PositionValuation(
                instrument=position.instrument,
                quantity=position.quantity,
                average_cost=position.average_cost,
                cost_basis=cost_basis,
                market_price=price,
                market_value=market_value,
                unrealized_gain=gain,
                unrealized_gain_percent=gain_percent,
                realized_gain=position.realized_gain,
                income=position.income,
                costs=position.costs,
                weight=weight,
            )
        )

    return PortfolioValuation(
        portfolio_id=portfolio.id,
        base_currency=base,
        positions=tuple(valuations),
        invested=invested,
        market_value=total_market_value,
        unrealized_gain=unrealized,
        realized_gain=realized,
        income=income,
        costs=costs,
        unpriced_symbols=tuple(sorted(unpriced)),
    )


__all__ = ["PortfolioValuation", "PositionValuation", "valuate"]
