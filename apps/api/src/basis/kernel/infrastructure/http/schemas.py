"""Shared HTTP schemas for values used across contexts."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from basis.kernel.domain.currency import Currency
from basis.kernel.domain.money import Money


class MoneySchema(BaseModel):
    """A monetary amount.

    ``amount`` is the exact decimal as a string (never a float). ``numeric`` is
    a float approximation provided for charts and quick client-side display;
    authoritative arithmetic always happens on the server.
    """

    amount: str
    currency: str = Field(min_length=3, max_length=5)
    numeric: float

    @classmethod
    def from_money(cls, money: Money) -> MoneySchema:
        return cls(
            amount=str(money.amount),
            currency=money.currency.code,
            numeric=float(money.amount),
        )

    def to_money(self) -> Money:
        return Money(amount=Decimal(self.amount), currency=Currency.of(self.currency))


__all__ = ["MoneySchema"]
