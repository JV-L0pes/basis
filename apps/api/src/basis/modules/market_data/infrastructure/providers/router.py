"""Provider routing and caching for market data."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date

from basis.kernel.domain.clock import Clock
from basis.kernel.infrastructure.cache import TtlCache
from basis.logging import get_logger
from basis.modules.market_data.domain.models import PricePoint
from basis.modules.market_data.domain.ports import (
    IndexPointView,
    MacroProvider,
    QuoteProvider,
    QuoteView,
)
from basis.modules.market_data.domain.value_objects import MacroSeriesCode
from basis.modules.market_data.infrastructure.providers.bcb import BcbSgsProvider
from basis.modules.market_data.infrastructure.providers.brapi import BrapiQuoteProvider
from basis.modules.market_data.infrastructure.providers.seed import (
    SeedMacroProvider,
    SeedQuoteProvider,
)
from basis.modules.market_data.infrastructure.providers.yahoo import YahooQuoteProvider

logger = get_logger("market_data.providers")


class RoutedQuoteProvider:
    """Routes symbols to the right provider, caches results and falls back to seed data."""

    def __init__(
        self,
        *,
        brapi: QuoteProvider,
        yahoo: QuoteProvider,
        seed: SeedQuoteProvider,
        cache: TtlCache[str, object],
        quote_ttl_seconds: int,
        allow_live: bool,
    ) -> None:
        self._brapi = brapi
        self._yahoo = yahoo
        self._seed = seed
        self._cache = cache
        self._ttl = quote_ttl_seconds
        self._allow_live = allow_live

    def primary_for(self, symbol: str) -> QuoteProvider:
        upper = symbol.upper()
        if upper in {"BTC", "ETH", "SOL"} or upper.endswith("=X") or upper.startswith("^"):
            return self._yahoo
        if "-" in upper or "." in upper:
            return self._yahoo
        return self._brapi

    async def get_quote(self, symbol: str) -> QuoteView | None:
        cached = self._cache.get(f"quote:{symbol.upper()}")
        if isinstance(cached, QuoteView):
            return cached
        quote = await self._resolve_quote(symbol)
        if quote is not None:
            self._cache.set(f"quote:{symbol.upper()}", quote, self._ttl)
        return quote

    async def get_quotes(self, symbols: Sequence[str]) -> Mapping[str, QuoteView]:
        quotes: dict[str, QuoteView] = {}
        for symbol in symbols:
            quote = await self.get_quote(symbol)
            if quote is not None:
                quotes[quote.symbol] = quote
        return quotes

    async def get_history(self, symbol: str, *, start: date, end: date) -> Sequence[PricePoint]:
        key = f"history:{symbol.upper()}:{start.isoformat()}:{end.isoformat()}"
        cached = self._cache.get(key)
        if isinstance(cached, tuple):
            return list(cached)
        points = await self._resolve_history(symbol, start=start, end=end)
        self._cache.set(key, tuple(points), self._ttl)
        return points

    # -- internals --------------------------------------------------------
    async def _resolve_quote(self, symbol: str) -> QuoteView | None:
        if self._allow_live:
            try:
                quote = await self.primary_for(symbol).get_quote(symbol)
                if quote is not None:
                    return quote
            except Exception as exc:  # noqa: BLE001 — fall back to the seed provider
                logger.warning(
                    "quote_provider_failed", symbol=symbol, reason=type(exc).__name__
                )
        return await self._seed.get_quote(symbol)

    async def _resolve_history(self, symbol: str, *, start: date, end: date) -> Sequence[PricePoint]:
        if self._allow_live:
            try:
                points = await self.primary_for(symbol).get_history(symbol, start=start, end=end)
                if points:
                    return points
            except Exception as exc:  # noqa: BLE001 — fall back to the seed provider
                logger.warning(
                    "history_provider_failed", symbol=symbol, reason=type(exc).__name__
                )
        return await self._seed.get_history(symbol, start=start, end=end)


class CachedMacroProvider:
    """Macro provider with a TTL cache and a deterministic fallback."""

    def __init__(
        self,
        *,
        live: MacroProvider,
        fallback: SeedMacroProvider,
        cache: TtlCache[str, object],
        ttl_seconds: int,
        allow_live: bool,
    ) -> None:
        self._live = live
        self._fallback = fallback
        self._cache = cache
        self._ttl = ttl_seconds
        self._allow_live = allow_live

    async def get_series(
        self, code: MacroSeriesCode, *, start: date, end: date
    ) -> Sequence[IndexPointView]:
        key = f"macro:{code}:{start.isoformat()}:{end.isoformat()}"
        cached = self._cache.get(key)
        if isinstance(cached, tuple):
            return list(cached)

        series: Sequence[IndexPointView] = ()
        if self._allow_live:
            try:
                series = await self._live.get_series(code, start=start, end=end)
            except Exception as exc:  # noqa: BLE001 — fall back to deterministic data
                logger.warning("macro_provider_failed", code=str(code), reason=type(exc).__name__)
                series = ()
        if not series:
            series = await self._fallback.get_series(code, start=start, end=end)
        self._cache.set(key, tuple(series), self._ttl)
        return series

    async def latest(self, code: MacroSeriesCode) -> IndexPointView | None:
        cached = self._cache.get(f"macro:latest:{code}")
        if isinstance(cached, IndexPointView):
            return cached

        value: IndexPointView | None = None
        if self._allow_live:
            try:
                value = await self._live.latest(code)
            except Exception as exc:  # noqa: BLE001 — fall back to deterministic data
                logger.warning("macro_latest_failed", code=str(code), reason=type(exc).__name__)
        if value is None:
            value = await self._fallback.latest(code)
        if value is not None:
            self._cache.set(f"macro:latest:{code}", value, self._ttl)
        return value


@dataclass(frozen=True, slots=True)
class MarketDataProviders:
    """Everything the presentation layer needs to serve market data."""

    quotes: QuoteProvider
    macro: MacroProvider
    seed: SeedQuoteProvider


def build_market_data_providers(
    *,
    clock: Clock,
    timeout_seconds: float,
    quote_cache_ttl_seconds: int,
    brapi_token: str | None,
    allow_live_providers: bool,
) -> MarketDataProviders:
    """Wire providers, cache and fallbacks from settings."""
    cache: TtlCache[str, object] = TtlCache()
    seed = SeedQuoteProvider(clock=clock)
    quotes = RoutedQuoteProvider(
        brapi=BrapiQuoteProvider(clock=clock, timeout=timeout_seconds, token=brapi_token),
        yahoo=YahooQuoteProvider(clock=clock, timeout=timeout_seconds),
        seed=seed,
        cache=cache,
        quote_ttl_seconds=quote_cache_ttl_seconds,
        allow_live=allow_live_providers,
    )
    macro = CachedMacroProvider(
        live=BcbSgsProvider(clock=clock, timeout=timeout_seconds),
        fallback=SeedMacroProvider(clock=clock),
        cache=cache,
        ttl_seconds=max(quote_cache_ttl_seconds, 300),
        allow_live=allow_live_providers,
    )
    return MarketDataProviders(quotes=quotes, macro=macro, seed=seed)


__all__ = [
    "CachedMacroProvider",
    "MarketDataProviders",
    "RoutedQuoteProvider",
    "build_market_data_providers",
]
