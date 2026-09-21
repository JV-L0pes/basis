"""Yahoo Finance provider for crypto, FX and international tickers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal

from basis.kernel.domain.clock import Clock
from basis.kernel.domain.currency import BRL, Currency
from basis.kernel.domain.money import Money
from basis.logging import get_logger
from basis.modules.market_data.domain.models import PricePoint
from basis.modules.market_data.domain.ports import QuoteView
from basis.modules.market_data.domain.value_objects import QuoteSource
from basis.modules.market_data.infrastructure.providers._http import fetch_json
from basis.modules.market_data.infrastructure.providers._json import (
    as_decimal,
    as_mapping,
    as_sequence,
    as_str,
)

BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
DEFAULT_TIMEOUT_SECONDS = 10.0

logger = get_logger("market_data.yahoo")


class YahooQuoteProvider:
    """Quotes and daily closes from the public Yahoo Finance chart endpoint."""

    def __init__(self, *, clock: Clock, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self._clock = clock
        self._timeout = timeout

    @staticmethod
    def to_yahoo_symbol(symbol: str) -> str:
        """Map platform symbols to Yahoo symbols (``BTC`` -> ``BTC-USD``)."""
        upper = symbol.strip().upper()
        if upper in {"BTC", "ETH", "SOL"}:
            return f"{upper}-USD"
        return upper

    async def get_quote(self, symbol: str) -> QuoteView | None:
        result = await self._fetch_result(
            self.to_yahoo_symbol(symbol), params={"interval": "1d", "range": "1d"}
        )
        if result is None:
            return None

        meta = as_mapping(result.get("meta"))
        price = as_decimal(meta.get("regularMarketPrice"))
        if price is None:
            return None

        previous_close = as_decimal(meta.get("chartPreviousClose") or meta.get("previousClose"))
        change_percent = None
        if previous_close is not None and previous_close != 0:
            change_percent = (price - previous_close) / previous_close * 100

        as_of = self._clock.now()
        epoch = meta.get("regularMarketTime")
        if isinstance(epoch, (int, float)) and not isinstance(epoch, bool):
            as_of = datetime.fromtimestamp(float(epoch), tz=UTC)

        return QuoteView(
            symbol=symbol.strip().upper(),
            price=Money(price, self._currency_of(meta, symbol)),
            as_of=as_of,
            source=str(QuoteSource.YAHOO),
            change_percent=change_percent,
        )

    async def get_quotes(self, symbols: Sequence[str]) -> Mapping[str, QuoteView]:
        quotes: dict[str, QuoteView] = {}
        for symbol in symbols:
            quote = await self.get_quote(symbol)
            if quote is not None:
                quotes[quote.symbol] = quote
        return quotes

    async def get_history(self, symbol: str, *, start: date, end: date) -> Sequence[PricePoint]:
        yahoo_symbol = self.to_yahoo_symbol(symbol)
        result = await self._fetch_result(
            yahoo_symbol,
            params={
                "interval": "1d",
                "period1": str(_epoch(start)),
                "period2": str(_epoch(end)),
            },
        )
        if result is None:
            return []

        timestamps = [
            value for value in as_sequence(result.get("timestamp")) if isinstance(value, int)
        ]
        closes = self._closes_of(result)
        currency = self._currency_of(as_mapping(result.get("meta")), symbol)

        points: list[PricePoint] = []
        for epoch, close in zip(timestamps, closes, strict=False):
            if close is None:
                continue
            moment = datetime.fromtimestamp(float(epoch), tz=UTC).date()
            if start <= moment <= end:
                points.append(PricePoint(date=moment, close=Money(close, currency)))
        points.sort(key=lambda point: point.date)
        return points

    # -- internals --------------------------------------------------------
    async def _fetch_result(
        self, yahoo_symbol: str, *, params: Mapping[str, str]
    ) -> Mapping[str, object] | None:
        payload = await fetch_json(
            f"{BASE_URL}/{yahoo_symbol}", timeout=self._timeout, params=params
        )
        chart = as_mapping(as_mapping(payload).get("chart"))
        results = as_sequence(chart.get("result"))
        if not results:
            return None
        return as_mapping(results[0])

    @staticmethod
    def _closes_of(result: Mapping[str, object]) -> list[Decimal | None]:
        indicators = as_mapping(result.get("indicators"))
        quote_blocks = as_sequence(indicators.get("quote"))
        if not quote_blocks:
            return []
        return [as_decimal(value) for value in as_sequence(as_mapping(quote_blocks[0]).get("close"))]

    @staticmethod
    def _currency_of(meta: Mapping[str, object], symbol: str) -> Currency:
        del symbol  # the payload is authoritative; BRL is the platform default
        code = as_str(meta.get("currency"))
        if code is not None:
            try:
                return Currency.of(code)
            except Exception as exc:  # noqa: BLE001 — unknown code, fall back to BRL
                logger.debug("yahoo_unknown_currency", code=code, reason=type(exc).__name__)
        return BRL


def _epoch(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp())


__all__ = ["YahooQuoteProvider"]
