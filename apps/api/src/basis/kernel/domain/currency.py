"""ISO 4217 currencies plus the crypto units the platform quotes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from basis.kernel.domain.errors import ValidationError


class UnknownCurrencyError(ValidationError):
    """Raised when a currency code is not part of the registry."""


class CurrencyKind(StrEnum):
    FIAT = "fiat"
    CRYPTO = "crypto"


@dataclass(frozen=True, slots=True)
class Currency:
    """A unit of account.

    ``exponent`` is the number of decimal places that are meaningful for the
    unit (ISO 4217 calls this the "minor unit" exponent: BRL has 2, JPY has 0,
    BTC has 8).
    """

    code: str
    name: str
    numeric: str | None
    exponent: int
    kind: CurrencyKind = CurrencyKind.FIAT

    def __post_init__(self) -> None:
        normalized = self.code.strip().upper()
        if not (2 <= len(normalized) <= 5) or not normalized.isalpha():
            raise ValidationError(
                "Currency code must be 2 to 5 letters", details={"code": self.code}
            )
        if not 0 <= self.exponent <= 18:
            raise ValidationError(
                "Currency exponent must be between 0 and 18",
                details={"code": self.code, "exponent": self.exponent},
            )
        object.__setattr__(self, "code", normalized)

    def __str__(self) -> str:
        return self.code

    @staticmethod
    def of(code: str) -> Currency:
        """Look up a currency by code, case-insensitively."""
        try:
            return _REGISTRY[code.strip().upper()]
        except KeyError as exc:
            raise UnknownCurrencyError("Unknown currency code", details={"code": code}) from exc


def _fiat(code: str, name: str, numeric: str, exponent: int = 2) -> Currency:
    return Currency(code=code, name=name, numeric=numeric, exponent=exponent)


def _crypto(code: str, name: str, exponent: int) -> Currency:
    return Currency(code=code, name=name, numeric=None, exponent=exponent, kind=CurrencyKind.CRYPTO)


BRL = _fiat("BRL", "Brazilian real", "986")
USD = _fiat("USD", "United States dollar", "840")
EUR = _fiat("EUR", "Euro", "978")
GBP = _fiat("GBP", "Pound sterling", "826")
JPY = _fiat("JPY", "Japanese yen", "392", exponent=0)
CHF = _fiat("CHF", "Swiss franc", "756")
CAD = _fiat("CAD", "Canadian dollar", "124")
AUD = _fiat("AUD", "Australian dollar", "036")
ARS = _fiat("ARS", "Argentine peso", "032")
CLP = _fiat("CLP", "Chilean peso", "152", exponent=0)
MXN = _fiat("MXN", "Mexican peso", "484")
CNY = _fiat("CNY", "Renminbi", "156")

BTC = _crypto("BTC", "Bitcoin", exponent=8)
ETH = _crypto("ETH", "Ether", exponent=18)
SOL = _crypto("SOL", "Solana", exponent=9)
USDT = _crypto("USDT", "Tether", exponent=6)
USDC = _crypto("USDC", "USD Coin", exponent=6)

_ALL = (
    BRL,
    USD,
    EUR,
    GBP,
    JPY,
    CHF,
    CAD,
    AUD,
    ARS,
    CLP,
    MXN,
    CNY,
    BTC,
    ETH,
    SOL,
    USDT,
    USDC,
)

_REGISTRY: dict[str, Currency] = {currency.code: currency for currency in _ALL}

__all__ = [
    "ARS",
    "AUD",
    "BRL",
    "BTC",
    "CAD",
    "CHF",
    "CLP",
    "CNY",
    "ETH",
    "EUR",
    "GBP",
    "JPY",
    "MXN",
    "SOL",
    "USD",
    "USDC",
    "USDT",
    "Currency",
    "CurrencyKind",
    "UnknownCurrencyError",
]
