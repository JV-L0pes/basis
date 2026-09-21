"""Unit tests for the currency registry and value object."""

from __future__ import annotations

import pytest

from basis.kernel.domain.currency import (
    BRL,
    BTC,
    JPY,
    USD,
    Currency,
    CurrencyKind,
    UnknownCurrencyError,
)
from basis.kernel.domain.errors import ValidationError


class TestRegistry:
    def test_lookup_is_case_insensitive(self) -> None:
        assert Currency.of("brl") is BRL
        assert Currency.of("  usd ") is USD

    def test_unknown_code_raises(self) -> None:
        with pytest.raises(UnknownCurrencyError):
            Currency.of("XYZ")

    def test_jpy_has_zero_exponent(self) -> None:
        assert JPY.exponent == 0
        assert JPY.numeric == "392"

    def test_crypto_has_no_numeric_code(self) -> None:
        assert BTC.kind == CurrencyKind.CRYPTO
        assert BTC.numeric is None
        assert BTC.exponent == 8

    def test_unknown_currency_error_is_a_validation_error(self) -> None:
        assert issubclass(UnknownCurrencyError, ValidationError)


class TestValidation:
    def test_code_is_normalized_to_uppercase(self) -> None:
        assert Currency(code="brl", name="Real", numeric="986", exponent=2).code == "BRL"

    def test_rejects_non_alpha_code(self) -> None:
        with pytest.raises(ValidationError, match="must be 2 to 5 letters"):
            Currency(code="B1L", name="Invalid", numeric=None, exponent=2)

    def test_rejects_negative_exponent(self) -> None:
        with pytest.raises(ValidationError, match="between 0 and 18"):
            Currency(code="BRL", name="Real", numeric="986", exponent=-1)

    def test_str_returns_code(self) -> None:
        assert str(BRL) == "BRL"
