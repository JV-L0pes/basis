"""Market data value objects: identifiers, tickers and macro series codes."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

from basis.kernel.domain.errors import ValidationError

_MIC_PATTERN = re.compile(r"^[A-Z]{4}(-[A-Z]{4})?$")
_ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_CFI_PATTERN = re.compile(r"^[A-Z]{6}$")
_B3_PATTERN = re.compile(r"^[A-Z]{4}\d{1,2}$")
_GENERAL_SYMBOL_PATTERN = re.compile(r"^[A-Z0-9^][A-Z0-9.\-^=]{1,14}$")

_ISIN_LETTER_OFFSET = ord("A") - 10  # 'A' maps to 10 in the Luhn expansion


@dataclass(frozen=True, slots=True)
class TickerSymbol:
    """A tradable symbol (``PETR4``, ``IGUATEMI11``, ``BTC-USD``, ``^BVSP``)."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not _GENERAL_SYMBOL_PATTERN.match(normalized):
            raise ValidationError("Invalid ticker symbol", details={"symbol": self.value})
        object.__setattr__(self, "value", normalized)

    @property
    def is_b3_ticker(self) -> bool:
        """B3 equities and FIIs use four letters followed by one or two digits."""
        return bool(_B3_PATTERN.match(self.value))

    @property
    def is_crypto_or_fx(self) -> bool:
        return "-" in self.value or "=X" in self.value or self.value in {"BTC", "ETH", "SOL"}

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Mic:
    """ISO 10383 market identifier code (``BVMF`` for B3)."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not _MIC_PATTERN.match(normalized):
            raise ValidationError("Invalid MIC code", details={"mic": self.value})
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Isin:
    """ISO 6166 international securities identification number (with Luhn check)."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not _ISIN_PATTERN.match(normalized):
            raise ValidationError("Invalid ISIN format", details={"isin": self.value})

        digits = "".join(
            str(ord(character) - _ISIN_LETTER_OFFSET) if character.isalpha() else character
            for character in normalized
        )
        total = 0
        for index, character in enumerate(reversed(digits)):
            digit = int(character)
            if index % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        if total % 10 != 0:
            raise ValidationError("ISIN has an invalid check digit", details={"isin": self.value})
        object.__setattr__(self, "value", normalized)

    @property
    def country(self) -> str:
        """ISO 3166 alpha-2 country prefix."""
        return self.value[:2]

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class CfiCode:
    """ISO 10962 classification of financial instruments (format check only)."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not _CFI_PATTERN.match(normalized):
            raise ValidationError("Invalid CFI code", details={"cfi": self.value})
        object.__setattr__(self, "value", normalized)

    @property
    def category(self) -> str:
        """First letter of the CFI code: the instrument category."""
        return self.value[0]

    def __str__(self) -> str:
        return self.value


class QuoteSource(StrEnum):
    """Where a quote came from."""

    BRAPI = "brapi"
    BCB = "bcb"
    YAHOO = "yahoo"
    SEED = "seed"


class MacroSeriesCode(StrEnum):
    """Brazilian macro series published by the BCB SGS system."""

    SELIC = "selic"
    CDI = "cdi"
    IPCA = "ipca"
    USD_BRL = "usd_brl"

    @classmethod
    def parse(cls, value: str) -> MacroSeriesCode:
        """Parse an API code (case and whitespace insensitive)."""
        try:
            return cls(value.strip().lower())
        except ValueError as exc:
            raise ValidationError("Unknown macro series code", details={"code": value}) from exc

    @property
    def bcb_sgs_id(self) -> int:
        return _SGS_IDS[self]

    @property
    def label(self) -> str:
        return _LABELS[self]

    @property
    def unit(self) -> str:
        return _UNITS[self]


_SGS_IDS: dict[MacroSeriesCode, int] = {
    MacroSeriesCode.SELIC: 11,
    MacroSeriesCode.CDI: 12,
    MacroSeriesCode.IPCA: 433,
    MacroSeriesCode.USD_BRL: 1,
}

_LABELS: dict[MacroSeriesCode, str] = {
    MacroSeriesCode.SELIC: "SELIC",
    MacroSeriesCode.CDI: "CDI",
    MacroSeriesCode.IPCA: "IPCA",
    MacroSeriesCode.USD_BRL: "USD/BRL",
}

_UNITS: dict[MacroSeriesCode, str] = {
    MacroSeriesCode.SELIC: "% a.a.",
    MacroSeriesCode.CDI: "% a.m.",
    MacroSeriesCode.IPCA: "% a.m.",
    MacroSeriesCode.USD_BRL: "BRL",
}


__all__ = [
    "CfiCode",
    "Isin",
    "MacroSeriesCode",
    "Mic",
    "QuoteSource",
    "TickerSymbol",
]
