"""Provider routing and caching for market data."""

from __future__ import annotations

import asyncio
from collections.abc import Coroutine, Mapping, Sequence
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

# Upstream calls run concurrently, but never more than this per request.
MAX_CONCURRENT_FETCHES = 6


class RoutedQuoteProvider:
    """Routes symbols to the right provider, caches results and falls back to seed data.

    Live providers never block a request: the deterministic series answers
    immediately and a background task refreshes the cache with the upstream
    value, so the next read is live. This is the usual market data trade-off —
    the screen never waits on a flaky vendor.
    """

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
        self._refreshes: set[asyncio.Task[None]] = set()

    def primary_for(self, symbol: str) -> QuoteProvider:
        upper = symbol.upper()
        if upper in {"BTC", "ETH", "SOL"} or upper.endswith("=X") or upper.startswith("^"):
            return self._yahoo
        if "-" in upper or "." in upper:
            return self._yahoo
        return self._brapi

    async def get_quote(self, symbol: str) -> QuoteView | None:
        normalized = symbol.upper()
        cached = self._cache.get(f"quote:{normalized}")
        if isinstance(cached, QuoteView):
            return cached

        if self._allow_live:
            self._schedule_refresh(self._refresh_quote(normalized))
        quote = await self._seed.get_quote(symbol)
        if quote is not None:
            self._cache.set(f"quote:{normalized}", quote, self._ttl)
        return quote

    async def get_quotes(self, symbols: Sequence[str]) -> Mapping[str, QuoteView]:
        """Fetch the batch concurrently: latency is the slowest symbol, not the sum."""
        unique = list(dict.fromkeys(symbol.upper() for symbol in symbols))
        if not unique:
            return {}
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)

        async def fetch(symbol: str) -> QuoteView | None:
            async with semaphore:
                return await self.get_quote(symbol)

        results = await asyncio.gather(*(fetch(symbol) for symbol in unique))
        return {quote.symbol: quote for quote in results if quote is not None}

    async def get_history(self, symbol: str, *, start: date, end: date) -> Sequence[PricePoint]:
        key = f"history:{symbol.upper()}:{start.isoformat()}:{end.isoformat()}"
        cached = self._cache.get(key)
        if isinstance(cached, tuple):
            return list(cached)

        if self._allow_live:
            self._schedule_refresh(self._refresh_history(symbol, start=start, end=end, key=key))
        points = await self._seed.get_history(symbol, start=start, end=end)
        self._cache.set(key, tuple(points), self._ttl)
        return list(points)

    async def wait_for_refreshes(self) -> None:
        """Await the in-flight background refreshes (used by tests and shutdown)."""
        while self._refreshes:
            await asyncio.gather(*tuple(self._refreshes), return_exceptions=True)

    # -- internals --------------------------------------------------------
    def _schedule_refresh(self, coroutine: Coroutine[object, object, None]) -> None:
        task = asyncio.create_task(coroutine)
        self._refreshes.add(task)
        task.add_done_callback(self._refreshes.discard)

    async def _refresh_quote(self, symbol: str) -> None:
        try:
            quote = await self.primary_for(symbol).get_quote(symbol)
        except Exception as exc:  # noqa: BLE001 — the seed fallback is already served
            logger.warning("quote_provider_failed", symbol=symbol, reason=type(exc).__name__)
            return
        if quote is not None:
            self._cache.set(f"quote:{symbol}", quote, self._ttl)

    async def _refresh_history(self, symbol: str, *, start: date, end: date, key: str) -> None:
        try:
            points = await self.primary_for(symbol).get_history(symbol, start=start, end=end)
        except Exception as exc:  # noqa: BLE001 — the seed series is already served
            logger.warning("history_provider_failed", symbol=symbol, reason=type(exc).__name__)
            return
        if points:
            self._cache.set(key, tuple(points), self._ttl)


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
