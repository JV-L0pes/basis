"""Unit tests for portfolio domain rules: ledger fold, valuation and targets."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from basis.kernel.domain.assets import AssetClass
from basis.kernel.domain.clock import FrozenClock
from basis.kernel.domain.currency import BRL, USD, Currency
from basis.kernel.domain.errors import InvariantViolationError, ValidationError
from basis.kernel.domain.identifiers import new_id
from basis.kernel.domain.money import Money
from basis.modules.portfolio.domain.models import Portfolio, Transaction
from basis.modules.portfolio.domain.valuation import valuate
from basis.modules.portfolio.domain.value_objects import (
    AllocationTargets,
    InstrumentRef,
    PortfolioStatus,
    TargetAllocation,
    TransactionKind,
)

MOMENT = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
TODAY = MOMENT.date()

PETR4 = InstrumentRef(
    instrument_id=new_id(),
    symbol="PETR4",
    asset_class=AssetClass.EQUITY,
    currency=BRL,
)
VALE3 = InstrumentRef(
    instrument_id=new_id(),
    symbol="VALE3",
    asset_class=AssetClass.EQUITY,
    currency=BRL,
)


def money(amount: str, currency: Currency = BRL) -> Money:
    return Money.parse(amount, currency)


def transaction(
    instrument: InstrumentRef = PETR4,
    kind: TransactionKind = TransactionKind.BUY,
    quantity: str = "100",
    price: str = "10.00",
    fees: str = "0",
    trade_date: date = TODAY,
) -> Transaction:
    return Transaction.record(
        instrument=instrument,
        kind=kind,
        trade_date=trade_date,
        quantity=Decimal(quantity),
        price=money(price, instrument.currency),
        fees=money(fees, instrument.currency),
        clock=FrozenClock(MOMENT),
    )


def open_portfolio(clock: FrozenClock | None = None) -> Portfolio:
    return Portfolio.open(
        client_id=uuid4(),
        name="Carteira Principal",
        base_currency=BRL,
        clock=clock or FrozenClock(MOMENT),
    )


class TestTransactionValidation:
    def test_rejects_non_positive_quantity(self) -> None:
        with pytest.raises(ValidationError, match="quantity must be positive"):
            Transaction.record(
                instrument=PETR4,
                kind=TransactionKind.BUY,
                trade_date=TODAY,
                quantity=Decimal(0),
                price=money("10.00"),
                clock=FrozenClock(MOMENT),
            )

    def test_rejects_currency_mismatch(self) -> None:
        with pytest.raises(ValidationError, match="currency must match"):
            Transaction.record(
                instrument=PETR4,
                kind=TransactionKind.BUY,
                trade_date=TODAY,
                quantity=Decimal(1),
                price=money("10.00", USD),
                clock=FrozenClock(MOMENT),
            )

    def test_gross_value_is_quantity_times_price(self) -> None:
        assert transaction(quantity="100", price="10.00").gross_value == money("1000.00")

    def test_cash_flow_signs(self) -> None:
        assert transaction(kind=TransactionKind.BUY, quantity="10", price="10").cash_flow == money("-100.00")
        assert transaction(kind=TransactionKind.SELL, quantity="10", price="10").cash_flow == money("100.00")
        assert transaction(kind=TransactionKind.DIVIDEND, quantity="1", price="25").cash_flow == money("25.00")
        assert transaction(kind=TransactionKind.FEE, quantity="1", price="5").cash_flow == money("-5.00")


class TestPositionFold:
    def _portfolio_with(self, *transactions: Transaction) -> Portfolio:
        portfolio = open_portfolio()
        for item in transactions:
            portfolio.record_transaction(item, clock=FrozenClock(MOMENT))
        return portfolio

    def test_buy_computes_weighted_average_cost(self) -> None:
        portfolio = self._portfolio_with(
            transaction(quantity="100", price="10.00", fees="5.00"),
            transaction(quantity="100", price="20.00", fees="5.00"),
        )
        position = portfolio.positions()[0]
        assert position.quantity == Decimal(200)
        # (1000 + 5 + 2000 + 5) / 200 = 15.05
        assert position.average_cost == money("15.05")
        assert position.cost_basis == money("3010.00")

    def test_sell_realizes_gain_and_keeps_average_cost(self) -> None:
        portfolio = self._portfolio_with(
            transaction(quantity="100", price="10.00"),
            transaction(
                kind=TransactionKind.SELL, quantity="40", price="15.00", fees="2.00"
            ),
        )
        position = portfolio.positions()[0]
        assert position.quantity == Decimal(60)
        assert position.average_cost == money("10.00")
        # proceeds 600 - 2 = 598; cost 400 -> gain 198
        assert position.realized_gain == money("198.00")

    def test_selling_everything_resets_average_cost(self) -> None:
        portfolio = self._portfolio_with(
            transaction(quantity="10", price="10.00"),
            transaction(kind=TransactionKind.SELL, quantity="10", price="12.00"),
        )
        position = portfolio.positions()[0]
        assert position.quantity == Decimal(0)
        assert position.average_cost == money("0.00")
        assert position.realized_gain == money("20.00")

    def test_overselling_is_rejected(self) -> None:
        portfolio = open_portfolio()
        portfolio.record_transaction(transaction(quantity="10"), clock=FrozenClock(MOMENT))
        with pytest.raises(InvariantViolationError, match="Cannot sell more"):
            portfolio.record_transaction(
                transaction(kind=TransactionKind.SELL, quantity="11"),
                clock=FrozenClock(MOMENT),
            )

    def test_dividends_accumulate_as_income(self) -> None:
        portfolio = self._portfolio_with(
            transaction(quantity="100", price="10.00"),
            transaction(kind=TransactionKind.DIVIDEND, quantity="1", price="50.00", fees="1.00"),
        )
        position = portfolio.positions()[0]
        assert position.quantity == Decimal(100)
        assert position.income == money("49.00")
        assert position.net_result == money("48.00")  # 49 income - 1 cost

    def test_fees_accumulate_as_costs(self) -> None:
        portfolio = self._portfolio_with(
            transaction(quantity="100", price="10.00", fees="4.00"),
            transaction(kind=TransactionKind.FEE, quantity="1", price="6.00"),
        )
        position = portfolio.positions()[0]
        assert position.costs == money("10.00")
        assert position.net_result == money("-10.00")

    def test_positions_are_ordered_by_symbol(self) -> None:
        portfolio = self._portfolio_with(transaction(instrument=PETR4), transaction(instrument=VALE3))
        assert [position.instrument.symbol for position in portfolio.positions()] == [
            "PETR4",
            "VALE3",
        ]


class TestPortfolioRules:
    def test_future_transactions_are_rejected(self) -> None:
        portfolio = open_portfolio()
        with pytest.raises(ValidationError, match="future"):
            portfolio.record_transaction(
                transaction(trade_date=TODAY + timedelta(days=1)), clock=FrozenClock(MOMENT)
            )

    def test_archived_portfolio_cannot_trade(self) -> None:
        clock = FrozenClock(MOMENT)
        portfolio = open_portfolio(clock)
        portfolio.archive(clock=clock)
        assert portfolio.status is PortfolioStatus.ARCHIVED
        with pytest.raises(InvariantViolationError, match="archived"):
            portfolio.record_transaction(transaction(), clock=clock)

    def test_targets_must_sum_to_one_hundred_percent(self) -> None:
        with pytest.raises(ValidationError, match="10000"):
            AllocationTargets(
                [
                    TargetAllocation(AssetClass.EQUITY, 6000),
                    TargetAllocation(AssetClass.FIXED_INCOME, 3000),
                ]
            )

    def test_targets_accept_exactly_one_hundred_percent(self) -> None:
        targets = AllocationTargets(
            [
                TargetAllocation(AssetClass.EQUITY, 6000),
                TargetAllocation(AssetClass.FIXED_INCOME, 4000),
            ]
        )
        assert len(targets) == 2
        assert targets.weight_of(AssetClass.EQUITY) == Decimal("0.6")
        assert targets.weight_of(AssetClass.CRYPTO) == Decimal(0)

    def test_duplicate_asset_classes_are_rejected(self) -> None:
        with pytest.raises(ValidationError, match="only once"):
            AllocationTargets(
                [
                    TargetAllocation(AssetClass.EQUITY, 5000),
                    TargetAllocation(AssetClass.EQUITY, 5000),
                ]
            )

    def test_setting_targets_records_event(self) -> None:
        clock = FrozenClock(MOMENT)
        portfolio = open_portfolio(clock)
        portfolio.pull_events()
        portfolio.set_targets(
            AllocationTargets([TargetAllocation(AssetClass.EQUITY, 10_000)]), clock=clock
        )
        events = portfolio.pull_events()
        assert len(events) == 1
        assert events[0].name == "portfolio.allocation_targets_set"


class TestValuation:
    def _portfolio(self) -> Portfolio:
        clock = FrozenClock(MOMENT)
        portfolio = open_portfolio(clock)
        portfolio.record_transaction(
            transaction(quantity="100", price="10.00", fees="0"), clock=clock
        )
        portfolio.record_transaction(
            transaction(instrument=VALE3, quantity="10", price="60.00"), clock=clock
        )
        portfolio.record_transaction(
            transaction(kind=TransactionKind.DIVIDEND, quantity="1", price="30.00"), clock=clock
        )
        return portfolio

    def test_valuation_marks_positions_to_market(self) -> None:
        valuation = valuate(
            self._portfolio(), {"PETR4": money("12.00"), "VALE3": money("61.00")}
        )
        assert valuation.invested == money("1600.00")
        assert valuation.market_value == money("1810.00")
        assert valuation.unrealized_gain == money("210.00")
        assert valuation.income == money("30.00")
        assert valuation.net_result == money("240.00")
        assert valuation.return_percent == Decimal("15.00")
        assert valuation.unpriced_symbols == ()

    def test_unpriced_symbols_are_reported(self) -> None:
        valuation = valuate(self._portfolio(), {"PETR4": money("12.00")})
        assert valuation.unpriced_symbols == ("VALE3",)
        assert valuation.market_value == money("1200.00")
        assert valuation.positions[1].market_value is None

    def test_weights_are_shares_of_market_value(self) -> None:
        valuation = valuate(
            self._portfolio(), {"PETR4": money("10.00"), "VALE3": money("60.00")}
        )
        petr = valuation.positions[0]
        vale = valuation.positions[1]
        assert petr.weight == Decimal("0.6250")
        assert vale.weight == Decimal("0.3750")
