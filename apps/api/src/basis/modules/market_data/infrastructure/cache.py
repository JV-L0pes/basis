"""TTL caching decorator for quote providers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date

from basis.kernel.infrastructure.cache import TtlCache
from basis.modules.market_data.domain.models import PricePoint
from basis.modules.market_data.domain.ports import QuoteProvider, QuoteView


class CachedQuoteProvider:
    """Wraps a :class:`QuoteProvider` with an in-process TTL cache.

    Quotes are cached per symbol and histories per ``(symbol, start, end)``
    window, so repeating a request inside the TTL never reaches the upstream
    provider. A zero TTL disables caching.
    """

    __slots__ = ("_history", "_provider", "_quotes", "_ttl_seconds")

    def __init__(self, provider: QuoteProvider, *, ttl_seconds: float) -> None:
        self._provider = provider
        self._ttl_seconds = ttl_seconds
        self._quotes: TtlCache[str, QuoteView] = TtlCache()
        self._history: TtlCache[tuple[str, date, date], tuple[PricePoint, ...]] = TtlCache()

    @property
    def ttl_seconds(self) -> float:
        return self._ttl_seconds

    async def get_quote(self, symbol: str) -> QuoteView | None:
        key = symbol.strip().upper()
        cached = self._quotes.get(key)
        if cached is not None:
            return cached
        quote = await self._provider.get_quote(symbol)
        if quote is None:
            return None
        self._quotes.set(key, quote, self._ttl_seconds)
        return quote

    async def get_quotes(self, symbols: Sequence[str]) -> Mapping[str, QuoteView]:
        quotes: dict[str, QuoteView] = {}
        missing: list[str] = []
        for symbol in symbols:
            cached = self._quotes.get(symbol.strip().upper())
            if cached is not None:
                quotes[cached.symbol] = cached
            else:
                missing.append(symbol)
        if not missing:
            return quotes
        fetched = await self._provider.get_quotes(missing)
        for quote in fetched.values():
            self._quotes.set(quote.symbol.strip().upper(), quote, self._ttl_seconds)
        quotes.update(fetched)
        return quotes

    async def get_history(self, symbol: str, *, start: date, end: date) -> Sequence[PricePoint]:
        key = (symbol.strip().upper(), start, end)
        cached = self._history.get(key)
        if cached is not None:
            return cached
        points = tuple(await self._provider.get_history(symbol, start=start, end=end))
        self._history.set(key, points, self._ttl_seconds)
        return points


__all__ = ["CachedQuoteProvider"]
