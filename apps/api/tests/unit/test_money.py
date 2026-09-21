"""Unit tests for exact monetary arithmetic."""

from __future__ import annotations

from decimal import Decimal

import pytest

from basis.kernel.domain.currency import BRL, USD, Currency
from basis.kernel.domain.errors import ValidationError
from basis.kernel.domain.money import Money, sum_money


def brl(value: str) -> Money:
    return Money.parse(value, BRL)


class TestConstruction:
    def test_rejects_floats(self) -> None:
        with pytest.raises(ValidationError, match="must be a Decimal"):
            Money(amount=1.5, currency=BRL)  # type: ignore[arg-type]

    def test_rejects_non_finite(self) -> None:
        with pytest.raises(ValidationError, match="must be finite"):
            Money(amount=Decimal("NaN"), currency=BRL)

    def test_rejects_excessive_scale(self) -> None:
        with pytest.raises(ValidationError, match="too many decimal places"):
            Money(amount=Decimal("0.0000000000001"), currency=BRL)

    def test_zero(self) -> None:
        assert Money.zero(BRL).amount == 0
        assert Money.zero(BRL).is_zero()

    def test_parse_invalid_string(self) -> None:
        with pytest.raises(ValidationError, match="Invalid decimal amount"):
            Money.parse("not-a-number", BRL)


class TestArithmetic:
    def test_addition(self) -> None:
        assert brl("10.50") + brl("0.50") == brl("11.00")

    def test_subtraction(self) -> None:
        assert brl("10.00") - brl("0.25") == brl("9.75")

    def test_currency_mismatch_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="different currencies"):
            _ = brl("10.00") + Money.parse("1.00", USD)

    def test_multiplication_by_decimal_and_int(self) -> None:
        assert brl("10.00") * Decimal("0.5") == brl("5.00")
        assert 3 * brl("10.00") == brl("30.00")

    def test_division(self) -> None:
        assert brl("10.00") / 4 == brl("2.50")

    def test_division_by_zero_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="divide money by zero"):
            _ = brl("10.00") / 0

    def test_division_rounds_to_the_kernel_precision(self) -> None:
        result = brl("1000.00") / 3
        assert result.amount == Decimal("333.333333333333")
        assert result.amount.as_tuple().exponent == -12

    def test_negation_and_abs(self) -> None:
        assert -brl("10.00") == brl("-10.00")
        assert abs(brl("-10.00")) == brl("10.00")

    def test_comparisons(self) -> None:
        assert brl("1.00") < brl("2.00")
        assert brl("2.00") >= brl("2.00")
        assert not brl("2.00") > brl("2.00")

    def test_sum_money(self) -> None:
        assert sum_money([brl("1.10"), brl("2.20")], BRL) == brl("3.30")


class TestRounding:
    def test_quantize_uses_currency_exponent(self) -> None:
        assert brl("1.005").quantize() == brl("1.00")
        assert brl("1.015").quantize() == brl("1.02")

    def test_quantize_zero_exponent_currency(self) -> None:
        jpy = Currency.of("JPY")
        assert Money.parse("100.6", jpy).quantize() == Money.parse("101", jpy)

    def test_percentage_rounds_to_minor_units(self) -> None:
        assert brl("100.00").percentage(Decimal("0.015")) == brl("1.50")
        # banker's rounding (half-even) is the accounting default: 0.015 -> 0.02, 0.025 -> 0.02
        assert brl("1.00").percentage(Decimal("0.015")) == brl("0.02")
        assert brl("1.00").percentage(Decimal("0.025")) == brl("0.02")
        assert brl("0.01").percentage(Decimal("0.5")) == brl("0.00")

    def test_minor_units(self) -> None:
        assert brl("123.45").as_minor_units() == 12345


class TestAllocation:
    def test_splits_without_losing_minor_units(self) -> None:
        parts = brl("100.00").allocate([Decimal("0.5"), Decimal("0.5")])
        assert parts == [brl("50.00"), brl("50.00")]

    def test_largest_remainder_distributes_leftovers(self) -> None:
        parts = brl("0.05").allocate([Decimal(1), Decimal(1), Decimal(1)])
        assert sum(part.amount for part in parts) == Decimal("0.05")
        assert sorted(part.amount for part in parts) == [
            Decimal("0.01"),
            Decimal("0.02"),
            Decimal("0.02"),
        ]

    def test_allocation_keeps_total_exactly(self) -> None:
        parts = brl("1000.00").allocate([Decimal("0.33"), Decimal("0.33"), Decimal("0.34")])
        assert sum(part.amount for part in parts) == Decimal("1000.00")

    def test_negative_amount_allocation_preserves_sign(self) -> None:
        parts = brl("-10.00").allocate([Decimal(1), Decimal(1)])
        assert parts == [brl("-5.00"), brl("-5.00")]

    def test_allocation_with_zero_weight(self) -> None:
        parts = brl("10.00").allocate([Decimal(1), Decimal(0)])
        assert parts == [brl("10.00"), brl("0.00")]

    def test_rejects_empty_weights(self) -> None:
        with pytest.raises(ValidationError, match="at least one weight"):
            brl("10.00").allocate([])

    def test_rejects_negative_weights(self) -> None:
        with pytest.raises(ValidationError, match="cannot be negative"):
            brl("10.00").allocate([Decimal("1.5"), Decimal("-0.5")])

    def test_rejects_zero_total_weight(self) -> None:
        with pytest.raises(ValidationError, match="positive value"):
            brl("10.00").allocate([Decimal(0), Decimal(0)])


class TestCurrencyConversion:
    def test_convert_applies_rate_and_rounds(self) -> None:
        converted = brl("100.00").convert(USD, Decimal("0.2"))
        assert converted == Money.parse("20.00", USD)

    def test_convert_same_currency_only_quantizes(self) -> None:
        assert brl("10.005").convert(BRL, Decimal(1)) == brl("10.00")

    def test_convert_rejects_non_positive_rate(self) -> None:
        with pytest.raises(ValidationError, match="rate must be positive"):
            brl("10.00").convert(USD, Decimal(0))
