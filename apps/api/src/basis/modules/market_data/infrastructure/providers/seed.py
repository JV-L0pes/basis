"""Deterministic offline provider used for tests and when live data is disabled."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
import hashlib
import random

from basis.kernel.domain.assets import AssetClass
from basis.kernel.domain.clock import Clock
from basis.kernel.domain.currency import BRL, USD, Currency
from basis.kernel.domain.money import Money
from basis.modules.market_data.domain.models import PricePoint
from basis.modules.market_data.domain.ports import IndexPointView, QuoteView
from basis.modules.market_data.domain.value_objects import MacroSeriesCode, QuoteSource

# Reference prices (BRL unless noted). Used as the deterministic baseline.
SEED_PRICES: Mapping[str, Decimal] = {
    "PETR4": Decimal("38.72"),
    "VALE3": Decimal("61.45"),
    "ITUB4": Decimal("33.10"),
    "BBDC4": Decimal("14.25"),
    "BBAS3": Decimal("27.80"),
    "MGLU3": Decimal("8.35"),
    "WEGE3": Decimal("52.90"),
    "ABEV3": Decimal("12.40"),
    "RENT3": Decimal("45.60"),
    "SUZB3": Decimal("58.15"),
    "IGUATEMI11": Decimal("89.30"),
    "HGLG11": Decimal("162.40"),
    "KNRI11": Decimal("148.75"),
    "MXRF11": Decimal("10.15"),
    "BOVA11": Decimal("128.60"),
    "IVVB11": Decimal("352.10"),
    "SMAL11": Decimal("104.30"),
    "BTC": Decimal("615000.00"),
    "ETH": Decimal("18500.00"),
    "SOL": Decimal("980.00"),
    "USD/BRL": Decimal("5.42"),
    "EUR/BRL": Decimal("5.88"),
    "^BVSP": Decimal("132450.00"),
    "TESOURO SELIC 2029": Decimal("15230.50"),
    "CDB 120% CDI 2027": Decimal("1520.40"),
}

# The symbols highlighted on the dashboard, in display order.
BLUE_CHIPS: tuple[str, ...] = (
    "^BVSP",
    "USDBRL=X",
    "PETR4",
    "VALE3",
    "ITUB4",
    "BBDC4",
    "BBAS3",
    "WEGE3",
    "IGUATEMI11",
    "BOVA11",
    "BTC",
)


@dataclass(frozen=True, slots=True)
class SeedInstrument:
    """Reference instrument used to bootstrap the catalog."""

    symbol: str
    name: str
    asset_class: AssetClass
    currency_code: str = "BRL"


# The catalog the platform ships with: B3 blue chips, FIIs, ETFs, crypto and
# fixed income (Brazilian retail portfolios are mostly fixed income).
SEED_INSTRUMENTS: tuple[SeedInstrument, ...] = (
    SeedInstrument("PETR4", "Petrobras PN", AssetClass.EQUITY),
    SeedInstrument("VALE3", "Vale ON", AssetClass.EQUITY),
    SeedInstrument("ITUB4", "Itaú Unibanco PN", AssetClass.EQUITY),
    SeedInstrument("BBDC4", "Bradesco PN", AssetClass.EQUITY),
    SeedInstrument("BBAS3", "Banco do Brasil ON", AssetClass.EQUITY),
    SeedInstrument("MGLU3", "Magazine Luiza ON", AssetClass.EQUITY),
    SeedInstrument("WEGE3", "WEG ON", AssetClass.EQUITY),
    SeedInstrument("IGUATEMI11", "Iguatemi FII", AssetClass.REAL_ESTATE),
    SeedInstrument("HGLG11", "CSHG Logística FII", AssetClass.REAL_ESTATE),
    SeedInstrument("BOVA11", "iShares Ibovespa ETF", AssetClass.ETF),
    SeedInstrument("BTC", "Bitcoin", AssetClass.CRYPTO),
    SeedInstrument("ETH", "Ether", AssetClass.CRYPTO),
    SeedInstrument("TESOURO2029", "Tesouro Selic 2029", AssetClass.FIXED_INCOME),
    SeedInstrument("CDB2027", "CDB 120% CDI 2027", AssetClass.FIXED_INCOME),
)

# Alternative symbols accepted by the seed provider.
_SYMBOL_ALIASES: Mapping[str, str] = {
    "USDBRL=X": "USD/BRL",
    "EURBRL=X": "EUR/BRL",
    "TESOURO2029": "TESOURO SELIC 2029",
    "CDB2027": "CDB 120% CDI 2027",
    "PETR4.SA": "PETR4",
    "VALE3.SA": "VALE3",
    "ITUB4.SA": "ITUB4",
}

# Crypto is quoted in BRL (as Brazilian exchanges do); international symbols
# such as ^BVSP and USD/BRL keep their own units.
_USD_SYMBOLS: frozenset[str] = frozenset()

# Per-symbol daily behaviour for the deterministic walk: fixed income drifts
# gently with almost no noise, crypto is wild, everything else sits in between.
_SEED_VOLATILITY: Mapping[str, Decimal] = {
    "TESOURO SELIC 2029": Decimal("0.0002"),
    "CDB 120% CDI 2027": Decimal("0.0003"),
    "IGUATEMI11": Decimal("0.011"),
    "HGLG11": Decimal("0.012"),
    "MXRF11": Decimal("0.010"),
    "BOVA11": Decimal("0.011"),
    "IVVB11": Decimal("0.012"),
    "^BVSP": Decimal("0.010"),
    "USDBRL=X": Decimal("0.007"),
    "EURBRL=X": Decimal("0.007"),
    "BTC": Decimal("0.035"),
    "ETH": Decimal("0.040"),
    "SOL": Decimal("0.045"),
}
_SEED_DRIFT: Mapping[str, Decimal] = {
    "TESOURO SELIC 2029": Decimal("0.00042"),
    "CDB 120% CDI 2027": Decimal("0.00046"),
    "BTC": Decimal("0.00060"),
    "ETH": Decimal("0.00050"),
    "SOL": Decimal("0.00040"),
}
_DEFAULT_VOLATILITY = Decimal("0.018")
_DEFAULT_DRIFT = Decimal("0.00025")


class SeedQuoteProvider:
    """Deterministic pseudo-market data with no network access."""

    def __init__(self, clock: Clock, prices: Mapping[str, Decimal] | None = None) -> None:
        self._clock = clock
        self._prices = dict(prices or SEED_PRICES)

    def known_symbols(self) -> Sequence[str]:
        return tuple(self._prices)

    def resolve(self, symbol: str) -> str | None:
        """Map a platform symbol (including aliases) to a seed table key."""
        upper = symbol.strip().upper()
        if upper in self._prices:
            return upper
        return _SYMBOL_ALIASES.get(upper)

    def base_price(self, symbol: str) -> Decimal | None:
        key = self.resolve(symbol)
        return self._prices.get(key) if key is not None else None

    def _currency_for(self, symbol: str) -> Currency:
        key = self.resolve(symbol) or symbol.upper()
        return USD if key in _USD_SYMBOLS else BRL

    async def get_quote(self, symbol: str) -> QuoteView | None:
        price = self.base_price(symbol)
        if price is None:
            return None
        moment = self._clock.now()
        return QuoteView(
            symbol=symbol.strip().upper(),
            price=Money(price, self._currency_for(symbol)),
            as_of=moment,
            source=str(QuoteSource.SEED),
            change_percent=self._daily_change(symbol, moment.date()) * 100,
        )

    async def get_quotes(self, symbols: Sequence[str]) -> Mapping[str, QuoteView]:
        quotes: dict[str, QuoteView] = {}
        for symbol in symbols:
            quote = await self.get_quote(symbol)
            if quote is not None:
                quotes[quote.symbol] = quote
        return quotes

    async def get_history(self, symbol: str, *, start: date, end: date) -> Sequence[PricePoint]:
        base = self.base_price(symbol)
        if base is None or end < start:
            return []

        key = self.resolve(symbol) or symbol.upper()
        currency = self._currency_for(symbol)
        days = [start + timedelta(days=offset) for offset in range((end - start).days + 1)]

        walk = [Decimal(1)]
        for moment in days[1:]:
            walk.append(walk[-1] * (Decimal(1) + self._daily_change(key, moment)))
        anchor = walk[-1]

        points: list[PricePoint] = []
        for moment, factor in zip(days, walk, strict=True):
            price = (base * factor / anchor).quantize(Decimal("0.01"))
            points.append(PricePoint(date=moment, close=Money(price, currency)))
        return points

    def _daily_change(self, symbol: str, moment: date) -> Decimal:
        """Deterministic daily return, stable across runs and per asset class."""
        key = self.resolve(symbol) or symbol.upper()
        digest = hashlib.sha256(f"{key}:{moment.isoformat()}".encode()).hexdigest()
        generator = random.Random(int(digest[:16], 16))  # noqa: S311 — deterministic, not cryptographic
        volatility = _SEED_VOLATILITY.get(key, _DEFAULT_VOLATILITY)
        drift = _SEED_DRIFT.get(key, _DEFAULT_DRIFT)
        noise = Decimal(str(round(generator.uniform(-1.0, 1.0), 6))) * volatility
        return drift + noise


class SeedMacroProvider:
    """Deterministic macro series, used when live providers are disabled.

    Rate series mirror the BCB SGS semantics: each point is the rate for that
    period (Selic and CDI are daily rates, IPCA is monthly), not a cumulative
    sum. ``USD/BRL`` is a price level and walks like an FX rate.
    """

    _DAILY_RATES: Mapping[MacroSeriesCode, Decimal] = {
        MacroSeriesCode.SELIC: Decimal("0.00041"),
        MacroSeriesCode.CDI: Decimal("0.00040"),
        MacroSeriesCode.IPCA: Decimal("0.0028"),
        MacroSeriesCode.USD_BRL: Decimal("0"),
    }

    def __init__(self, clock: Clock, base_usd: Decimal = Decimal("5.42")) -> None:
        self._clock = clock
        self._base_usd = base_usd

    async def get_series(
        self, code: MacroSeriesCode, *, start: date, end: date
    ) -> Sequence[IndexPointView]:
        if end < start:
            return []
        base_rate = self._DAILY_RATES[code]
        points: list[IndexPointView] = []
        value = self._base_usd if code is MacroSeriesCode.USD_BRL else base_rate
        for offset in range((end - start).days + 1):
            moment = start + timedelta(days=offset)
            if code is MacroSeriesCode.USD_BRL:
                generator = random.Random(  # noqa: S311 — deterministic
                    int(
                        hashlib.sha256(f"usd:{moment.isoformat()}".encode()).hexdigest()[:16],
                        16,
                    )
                )
                drift = Decimal(str(round(generator.uniform(-0.008, 0.008), 6)))
                value = (value * (Decimal(1) + drift)).quantize(Decimal("0.0001"))
            else:
                generator = random.Random(  # noqa: S311 — deterministic
                    int(
                        hashlib.sha256(f"{code}:{moment.isoformat()}".encode()).hexdigest()[:16],
                        16,
                    )
                )
                noise = Decimal(str(round(generator.uniform(-0.08, 0.08), 6)))
                value = (base_rate * (Decimal(1) + noise)).quantize(Decimal("0.000001"))
            points.append(IndexPointView(code=str(code), date=moment, value=value))
        return points

    async def latest(self, code: MacroSeriesCode) -> IndexPointView | None:
        today = self._clock.today()
        series = await self.get_series(code, start=today - timedelta(days=10), end=today)
        return series[-1] if series else None


__all__ = [
    "BLUE_CHIPS",
    "SEED_INSTRUMENTS",
    "SEED_PRICES",
    "SeedInstrument",
    "SeedMacroProvider",
    "SeedQuoteProvider",
]
