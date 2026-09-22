"""Regression tests for the provider router: fallbacks, cache and macro semantics."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from basis.kernel.domain.clock import FrozenClock
from basis.kernel.infrastructure.cache import TtlCache
from basis.modules.market_data.domain.models import PricePoint
from basis.modules.market_data.domain.ports import IndexPointView, QuoteView
from basis.modules.market_data.domain.value_objects import MacroSeriesCode
from basis.modules.market_data.infrastructure.providers.router import (
    CachedMacroProvider,
    RoutedQuoteProvider,
)
from basis.modules.market_data.infrastructure.providers.seed import (
    SeedMacroProvider,
    SeedQuoteProvider,
)

MOMENT = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
TODAY = MOMENT.date()
SELIC_DAILY = Decimal("0.00041")


class FailingMacroProvider:
    async def get_series(self, code, *, start, end):
        raise RuntimeError("provider offline")

    async def latest(self, code):
        raise RuntimeError("provider offline")


class FailingQuoteProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def get_quote(self, symbol: str) -> QuoteView | None:
        self.calls += 1
        raise RuntimeError("provider offline")

    async def get_quotes(self, symbols: Sequence[str]) -> Mapping[str, QuoteView]:
        del symbols
        return {}

    async def get_history(self, symbol: str, *, start: date, end: date) -> Sequence[PricePoint]:
        del symbol, start, end
        self.calls += 1
        raise RuntimeError("provider offline")


def cached_macro(*, allow_live: bool) -> CachedMacroProvider:
    clock = FrozenClock(MOMENT)
    return CachedMacroProvider(
        live=FailingMacroProvider(),
        fallback=SeedMacroProvider(clock),
        cache=TtlCache(),
        ttl_seconds=300,
        allow_live=allow_live,
    )


class TestSeedMacroSemantics:
    async def test_rate_series_report_the_rate_not_a_cumulative_sum(self) -> None:
        """Selic/CDI points are daily rates (BCB semantics), so they stay flat."""
        series = await SeedMacroProvider(FrozenClock(MOMENT)).get_series(
            MacroSeriesCode.SELIC, start=date(2026, 6, 1), end=date(2026, 6, 10)
        )
        assert len(series) == 10
        for point in series:
            # within 8% of the base daily rate, never a compounded total
            assert SELIC_DAILY * Decimal("0.9") < point.value < SELIC_DAILY * Decimal("1.1")

    async def test_latest_returns_a_plausible_annualised_rate(self) -> None:
        latest = await SeedMacroProvider(FrozenClock(MOMENT)).latest(MacroSeriesCode.SELIC)
        assert latest is not None
        annualised = (Decimal(1) + latest.value) ** 252 - Decimal(1)
        assert Decimal("0.05") < annualised < Decimal("0.25")

    async def test_usd_series_walks_like_a_price_level(self) -> None:
        series = await SeedMacroProvider(FrozenClock(MOMENT)).get_series(
            MacroSeriesCode.USD_BRL, start=date(2026, 6, 1), end=date(2026, 6, 10)
        )
        assert series[0].value > Decimal("4")
        assert series[0].value != series[-1].value


class TestCachedMacroProvider:
    async def test_latest_falls_back_to_the_seed_provider(self) -> None:
        """Regression: the fallback must ask for the latest point, not a 100-year sum."""
        provider = cached_macro(allow_live=True)

        latest = await provider.latest(MacroSeriesCode.SELIC)

        assert latest is not None
        assert isinstance(latest, IndexPointView)
        assert latest.value < Decimal("0.01"), "daily rate, not a compounded total"

    async def test_latest_uses_the_fallback_when_live_is_disabled(self) -> None:
        provider = cached_macro(allow_live=False)
        latest = await provider.latest(MacroSeriesCode.CDI)
        assert latest is not None
        assert latest.code == "cdi"

    async def test_latest_is_cached(self) -> None:
        provider = cached_macro(allow_live=False)
        first = await provider.latest(MacroSeriesCode.IPCA)
        second = await provider.latest(MacroSeriesCode.IPCA)
        assert first == second


class TestRoutedQuoteProvider:
    def routed(self, *, allow_live: bool) -> RoutedQuoteProvider:
        clock = FrozenClock(MOMENT)
        return RoutedQuoteProvider(
            brapi=FailingQuoteProvider(),
            yahoo=FailingQuoteProvider(),
            seed=SeedQuoteProvider(clock),
            cache=TtlCache(),
            quote_ttl_seconds=60,
            allow_live=allow_live,
        )

    async def test_falls_back_to_seed_when_every_provider_fails(self) -> None:
        quote = await self.routed(allow_live=True).get_quote("PETR4")
        assert quote is not None
        assert quote.source == "seed"

    async def test_history_falls_back_to_seed(self) -> None:
        points = await self.routed(allow_live=True).get_history(
            "PETR4", start=date(2026, 6, 1), end=date(2026, 6, 5)
        )
        assert len(points) == 5
        assert all(isinstance(point, PricePoint) for point in points)

    async def test_unknown_symbol_returns_none(self) -> None:
        assert await self.routed(allow_live=False).get_quote("NAOEXISTE") is None

    async def test_seed_history_anchors_the_last_close_on_the_base_price(self) -> None:
        points = await self.routed(allow_live=False).get_history(
            "PETR4", start=date(2026, 6, 1), end=date(2026, 6, 10)
        )
        assert points[-1].close.amount == Decimal("38.72")

    @pytest.mark.parametrize(
        ("symbol", "expected"),
        [("PETR4", "brapi"), ("BTC", "yahoo"), ("USDBRL=X", "yahoo"), ("^BVSP", "yahoo")],
    )
    def test_routes_symbols_to_the_right_provider(self, symbol: str, expected: str) -> None:
        provider = self.routed(allow_live=True)
        assert provider.primary_for(symbol).__class__ is getattr(
            provider, f"_{expected}"
        ).__class__
