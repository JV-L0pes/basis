"""BRAPI provider (brapi.dev) for B3 equities, FIIs and ETFs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime

from basis.kernel.domain.clock import Clock
from basis.kernel.domain.currency import BRL
from basis.kernel.domain.money import Money
from basis.modules.market_data.domain.models import PricePoint
from basis.modules.market_data.domain.ports import QuoteView
from basis.modules.market_data.domain.value_objects import QuoteSource
from basis.modules.market_data.infrastructure.providers._http import fetch_json
from basis.modules.market_data.infrastructure.providers._json import (
    as_decimal,
    as_mapping,
    as_sequence,
    as_str,
    parse_datetime,
    parse_iso_date,
)

BASE_URL = "https://brapi.dev/api/quote"
DEFAULT_TIMEOUT_SECONDS = 10.0


class BrapiQuoteProvider:
    """Quotes and daily history from brapi.dev."""

    def __init__(
        self,
        *,
        clock: Clock,
        token: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._clock = clock
        self._timeout = timeout
        self._token = token

    def _headers(self) -> Mapping[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    def _params(self, extra: Mapping[str, str] | None = None) -> Mapping[str, str]:
        params: dict[str, str] = {}
        if self._token:
            params["token"] = self._token
        if extra:
            params.update(extra)
        return params

    async def get_quote(self, symbol: str) -> QuoteView | None:
        quotes = await self.get_quotes([symbol])
        return quotes.get(symbol.strip().upper())

    async def get_quotes(self, symbols: Sequence[str]) -> Mapping[str, QuoteView]:
        if not symbols:
            return {}
        payload = await fetch_json(
            f"{BASE_URL}/{','.join(symbol.strip().upper() for symbol in symbols)}",
            timeout=self._timeout,
            params=self._params(),
        )
        results = as_sequence(as_mapping(payload).get("results"))
        quotes: dict[str, QuoteView] = {}
        for item in results:
            result = as_mapping(item)
            symbol = as_str(result.get("symbol"))
            price = as_decimal(result.get("regularMarketPrice"))
            if symbol is None or price is None:
                continue
            as_of = parse_datetime(result.get("regularMarketTime")) or self._clock.now()
            quotes[symbol.upper()] = QuoteView(
                symbol=symbol.upper(),
                price=Money(price, BRL),
                as_of=as_of,
                source=str(QuoteSource.BRAPI),
                change_percent=as_decimal(result.get("regularMarketChangePercent")),
            )
        return quotes

    async def get_history(self, symbol: str, *, start: date, end: date) -> Sequence[PricePoint]:
        days = max((end - start).days, 1)
        payload = await fetch_json(
            f"{BASE_URL}/{symbol.strip().upper()}",
            timeout=self._timeout,
            params=self._params({"range": f"{min(days, 1825)}d", "interval": "1d"}),
        )
        results = as_sequence(as_mapping(payload).get("results"))
        if not results:
            return []
        series = as_sequence(as_mapping(results[0]).get("historicalDataPrice"))
        points: list[PricePoint] = []
        for item in series:
            entry = as_mapping(item)
            close = as_decimal(entry.get("close"))
            moment = None
            epoch = entry.get("date")
            if isinstance(epoch, (int, float)) and not isinstance(epoch, bool):
                moment = datetime.fromtimestamp(float(epoch), tz=UTC).date()
            else:
                moment = parse_iso_date(entry.get("date"))
            if close is None or moment is None or not (start <= moment <= end):
                continue
            points.append(PricePoint(date=moment, close=Money(close, BRL)))
        points.sort(key=lambda point: point.date)
        return points


__all__ = ["BrapiQuoteProvider"]
