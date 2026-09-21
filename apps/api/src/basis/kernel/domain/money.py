"""Exact monetary arithmetic.

``Money`` is a value object backed by :class:`decimal.Decimal` — floating point
is never used for prices, quantities or balances.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from decimal import ROUND_FLOOR, ROUND_HALF_EVEN, Decimal, InvalidOperation
from typing import Self

from basis.kernel.domain.currency import Currency
from basis.kernel.domain.errors import ValidationError

MAX_SCALE = 12
_QUANTIZER = Decimal(1).scaleb(-MAX_SCALE)


def _bounded(amount: Decimal) -> Decimal:
    """Keep arithmetic results inside the supported precision.

    Multiplication and division can produce more decimals than money supports
    (for example averaging costs over odd quantities), so results are rounded
    half-even to :data:`MAX_SCALE` places instead of failing validation.
    """
    exponent = amount.as_tuple().exponent
    scale = -exponent if isinstance(exponent, int) and exponent < 0 else 0
    if scale <= MAX_SCALE:
        return amount
    return amount.quantize(_QUANTIZER, rounding=ROUND_HALF_EVEN)


@dataclass(frozen=True, slots=True)
class Money:
    """An amount of a currency, exact to 12 decimal places."""

    amount: Decimal
    currency: Currency

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            raise ValidationError(
                "Money amount must be a Decimal",
                details={"amount": repr(self.amount), "type": type(self.amount).__name__},
            )
        if not self.amount.is_finite():
            raise ValidationError(
                "Money amount must be finite", details={"amount": str(self.amount)}
            )
        exponent = self.amount.as_tuple().exponent
        scale = -exponent if isinstance(exponent, int) and exponent < 0 else 0
        if scale > MAX_SCALE:
            raise ValidationError(
                "Money amount has too many decimal places",
                details={"amount": str(self.amount), "max_scale": MAX_SCALE},
            )

    # -- constructors -----------------------------------------------------
    @classmethod
    def zero(cls, currency: Currency) -> Self:
        return cls(amount=Decimal(0), currency=currency)

    @classmethod
    def parse(cls, value: str, currency: Currency) -> Self:
        try:
            return cls(amount=Decimal(value), currency=currency)
        except InvalidOperation as exc:
            raise ValidationError("Invalid decimal amount", details={"value": value}) from exc

    # -- arithmetic -------------------------------------------------------
    def _check_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValidationError(
                "Cannot combine amounts in different currencies",
                details={"left": self.currency.code, "right": other.currency.code},
            )

    def __add__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, factor: Decimal | int) -> Money:
        if isinstance(factor, bool) or not isinstance(factor, (Decimal, int)):
            return NotImplemented
        return Money(_bounded(self.amount * Decimal(factor)), self.currency)

    __rmul__ = __mul__

    def __truediv__(self, divisor: Decimal | int) -> Money:
        if isinstance(divisor, bool) or not isinstance(divisor, (Decimal, int)):
            return NotImplemented
        decimal_divisor = Decimal(divisor)
        if decimal_divisor == 0:
            raise ValidationError("Cannot divide money by zero")
        return Money(_bounded(self.amount / decimal_divisor), self.currency)

    def __neg__(self) -> Money:
        return Money(-self.amount, self.currency)

    def __abs__(self) -> Money:
        return Money(abs(self.amount), self.currency)

    # -- comparisons ------------------------------------------------------
    def __lt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_same_currency(other)
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        self._check_same_currency(other)
        return self.amount >= other.amount

    # -- helpers ----------------------------------------------------------
    def is_zero(self) -> bool:
        return self.amount == 0

    def is_positive(self) -> bool:
        return self.amount > 0

    def is_negative(self) -> bool:
        return self.amount < 0

    def quantize(self, exponent: int | None = None, rounding: str = ROUND_HALF_EVEN) -> Money:
        """Round to ``exponent`` decimal places (defaults to the currency exponent)."""
        places = self.currency.exponent if exponent is None else exponent
        quantizer = Decimal(1).scaleb(-places)
        return Money(self.amount.quantize(quantizer, rounding=rounding), self.currency)

    def as_minor_units(self) -> int:
        """Return the amount expressed in the currency's minor units (cents)."""
        factor = Decimal(10) ** self.currency.exponent
        return int((self.amount * factor).to_integral_value(rounding=ROUND_HALF_EVEN))

    def percentage(self, rate: Decimal) -> Money:
        """Return ``self * rate`` rounded to the currency's minor unit."""
        if not isinstance(rate, Decimal):
            raise ValidationError("Percentage rate must be a Decimal")
        return Money(self.amount * rate, self.currency).quantize()

    def allocate(self, weights: Sequence[Decimal | int]) -> list[Money]:
        """Split this amount proportionally without losing a single minor unit.

        Uses the largest-remainder method, so ``sum(result) == self`` always.
        """
        if not weights:
            raise ValidationError("Allocation requires at least one weight")
        decimals = [Decimal(weight) for weight in weights]
        if any(weight < 0 for weight in decimals):
            raise ValidationError("Allocation weights cannot be negative")
        total = sum(decimals, Decimal(0))
        if total <= 0:
            raise ValidationError("Allocation weights must sum to a positive value")

        sign = Decimal(-1) if self.amount < 0 else Decimal(1)
        factor = Decimal(10) ** self.currency.exponent
        minor_units = int((abs(self.amount) * factor).to_integral_value(rounding=ROUND_HALF_EVEN))

        exact = [Decimal(minor_units) * weight / total for weight in decimals]
        floors = [int(value.to_integral_value(rounding=ROUND_FLOOR)) for value in exact]
        remainder = minor_units - sum(floors)
        for index in sorted(
            range(len(exact)), key=lambda i: (exact[i] - floors[i], i), reverse=True
        )[:remainder]:
            floors[index] += 1

        return [Money(sign * Decimal(units) / factor, self.currency) for units in floors]

    def convert(self, target: Currency, rate: Decimal) -> Money:
        """Convert using an explicit ``rate`` expressed as target per unit of self."""
        if rate <= 0:
            raise ValidationError("Conversion rate must be positive")
        if self.currency == target:
            return self.quantize(target.exponent)
        return Money(self.amount * rate, target).quantize(target.exponent)

    def __str__(self) -> str:
        return f"{self.amount} {self.currency.code}"


def sum_money(amounts: Iterable[Money], currency: Currency) -> Money:
    """Sum an iterable of amounts, requiring a common currency."""
    total = Money.zero(currency)
    for amount in amounts:
        total = total + amount
    return total


__all__ = ["MAX_SCALE", "Money", "sum_money"]
