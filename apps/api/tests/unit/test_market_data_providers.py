"""Unit tests for market-data providers (all HTTP mocked with respx)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import pytest
import respx

from basis.kernel.domain.clock import FrozenClock
from basis.kernel.domain.errors import ExternalServiceError
from basis.modules.market_data.domain.ports import IndexPointView
from basis.modules.market_data.domain.value_objects import MacroSeriesCode
from basis.modules.market_data.infrastructure.providers.bcb import BcbSgsProvider
from basis.modules.market_data.infrastructure.providers.brapi import BrapiQuoteProvider
from basis.modules.market_data.infrastructure.providers.seed import (
    BLUE_CHIPS,
    SEED_PRICES,
    SeedMacroProvider,
    SeedQuoteProvider,
)
from basis.modules.market_data.infrastructure.providers.yahoo import YahooQuoteProvider

MOMENT = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
TODAY = date(2026, 6, 15)

BRAPI_QUOTE_URL = "https://brapi.dev/api/quote/PETR4"
BRAPI_TOKEN_PARAMS = {"token": "test-token"}

BRAPI_PAYLOAD = {
    "results": [
        {
            "symbol": "PETR4",
            "shortName": "Petroleo Brasileiro",
            "regularMarketPrice": 38.72,
            "regularMarketChangePercent": 1.25,
            "regularMarketTime": "2026-06-01T17:00:00.000Z",
            "currency": "BRL",
        }
    ]
}


def _epoch(day: date) -> int:
    return int(datetime(day.year, day.month, day.day, tzinfo=UTC).timestamp())


class TestBrapiQuoteProvider:
    async def test_parses_happy_path(self) -> None:
        with respx.mock(assert_all_called=False) as mock:
            route = mock.get(BRAPI_QUOTE_URL, params=BRAPI_TOKEN_PARAMS).mock(
                return_value=httpx.Response(200, json=BRAPI_PAYLOAD)
            )
            provider = BrapiQuoteProvider(token="test-token", clock=FrozenClock(MOMENT))
            quote = await provider.get_quote("petr4")

        assert route.called
        assert quote is not None
        assert quote.symbol == "PETR4"
        assert quote.price.amount == Decimal("38.72")
        assert quote.price.currency.code == "BRL"
        assert quote.source == "brapi"
        assert quote.change_percent == Decimal("1.25")
        assert quote.as_of == datetime(2026, 6, 1, 17, 0, tzinfo=UTC)

    async def test_unknown_symbol_returns_none(self) -> None:
        with respx.mock(assert_all_called=False) as mock:
            mock.get("https://brapi.dev/api/quote/XPTO3", params=BRAPI_TOKEN_PARAMS).mock(
                return_value=httpx.Response(200, json={"results": []})
            )
            provider = BrapiQuoteProvider(token="test-token", clock=FrozenClock(MOMENT))
            assert await provider.get_quote("XPTO3") is None

    async def test_retries_5xx_then_succeeds(self) -> None:
        with respx.mock(assert_all_called=False) as mock:
            route = mock.get(BRAPI_QUOTE_URL, params=BRAPI_TOKEN_PARAMS).mock(
                side_effect=[
                    httpx.Response(500),
                    httpx.Response(200, json=BRAPI_PAYLOAD),
                ]
            )
            provider = BrapiQuoteProvider(token="test-token", clock=FrozenClock(MOMENT))
            quote = await provider.get_quote("PETR4")

        assert route.call_count == 2
        assert quote is not None
        assert quote.price.amount == Decimal("38.72")

    async def test_total_failure_raises_external_service_error(self) -> None:
        with respx.mock(assert_all_called=False) as mock:
            route = mock.get(BRAPI_QUOTE_URL, params=BRAPI_TOKEN_PARAMS).mock(
                return_value=httpx.Response(503)
            )
            provider = BrapiQuoteProvider(token="test-token", clock=FrozenClock(MOMENT))
            with pytest.raises(ExternalServiceError):
                await provider.get_quote("PETR4")

        assert route.call_count == 2

    async def test_transport_error_raises_external_service_error(self) -> None:
        with respx.mock(assert_all_called=False) as mock:
            mock.get(BRAPI_QUOTE_URL, params=BRAPI_TOKEN_PARAMS).mock(
                side_effect=httpx.ConnectError("boom")
            )
            provider = BrapiQuoteProvider(token="test-token", clock=FrozenClock(MOMENT))
            with pytest.raises(ExternalServiceError):
                await provider.get_quote("PETR4")

    async def test_history_parses_and_filters_the_range(self) -> None:
        start, end = date(2026, 6, 1), date(2026, 6, 3)
        payload = {
            "results": [
                {
                    "symbol": "PETR4",
                    "currency": "BRL",
                    "historicalDataPrice": [
                        {"date": _epoch(date(2026, 5, 29)), "close": 38.0},
                        {"date": _epoch(start), "close": 38.5},
                        {"date": _epoch(end), "close": 39.0},
                    ],
                }
            ]
        }
        with respx.mock(assert_all_called=False) as mock:
            mock.get(
                BRAPI_QUOTE_URL,
                params={**BRAPI_TOKEN_PARAMS, "range": "2d", "interval": "1d"},
            ).mock(return_value=httpx.Response(200, json=payload))
            provider = BrapiQuoteProvider(token="test-token", clock=FrozenClock(MOMENT))
            points = await provider.get_history("PETR4", start=start, end=end)

        assert [point.date for point in points] == [start, end]
        assert points[-1].close.amount == Decimal("39.0")


class TestBcbSgsProvider:
    BCB_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados"

    async def test_parses_dates_and_comma_decimals(self) -> None:
        payload = [
            {"data": "02/05/2026", "valor": "10,75"},
            {"data": "29/05/2026", "valor": "1.234,56"},
        ]
        with respx.mock(assert_all_called=False) as mock:
            route = mock.get(
                self.BCB_URL,
                params={
                    "formato": "json",
                    "dataInicial": "01/05/2026",
                    "dataFinal": "31/05/2026",
                },
            ).mock(return_value=httpx.Response(200, json=payload))
            provider = BcbSgsProvider(clock=FrozenClock(MOMENT))
            points = await provider.get_series(
                MacroSeriesCode.SELIC, start=date(2026, 5, 1), end=date(2026, 5, 31)
            )

        assert route.called
        assert [point.date for point in points] == [date(2026, 5, 2), date(2026, 5, 29)]
        assert [point.value for point in points] == [Decimal("10.75"), Decimal("1234.56")]
        assert all(point.code == "selic" for point in points)

    async def test_empty_response_yields_no_points(self) -> None:
        with respx.mock(assert_all_called=False) as mock:
            mock.get(self.BCB_URL).mock(return_value=httpx.Response(200, json=[]))
            provider = BcbSgsProvider(clock=FrozenClock(MOMENT))
            assert (
                await provider.get_series(
                    MacroSeriesCode.SELIC, start=date(2026, 5, 1), end=date(2026, 5, 31)
                )
                == []
            )
            assert await provider.latest(MacroSeriesCode.SELIC) is None

    async def test_latest_uses_the_last_thirty_days(self) -> None:
        end = TODAY
        start = date(2026, 5, 16)
        payload = [
            {"data": "16/05/2026", "valor": "10,50"},
            {"data": "15/06/2026", "valor": "10,75"},
        ]
        with respx.mock(assert_all_called=False) as mock:
            mock.get(
                self.BCB_URL,
                params={
                    "formato": "json",
                    "dataInicial": "16/05/2026",
                    "dataFinal": "15/06/2026",
                },
            ).mock(return_value=httpx.Response(200, json=payload))
            provider = BcbSgsProvider(clock=FrozenClock(datetime(2026, 6, 15, 19, 0, tzinfo=UTC)))
            point = await provider.latest(MacroSeriesCode.SELIC)

        assert point is not None
        assert point.date == end
        assert point.value == Decimal("10.75")
        assert start < end


class TestYahooQuoteProvider:
    BASE_URL = "https://query1.finance.yahoo.com"
    QUOTE_URL = f"{BASE_URL}/v8/finance/chart/BTC-USD"

    async def test_parses_chart_quote(self) -> None:
        payload = {
            "chart": {
                "result": [
                    {
                        "meta": {
                            "currency": "BRL",
                            "regularMarketPrice": 615000.0,
                            "regularMarketTime": 1748793600,
                            "previousClose": 600000.0,
                        }
                    }
                ],
                "error": None,
            }
        }
        with respx.mock(assert_all_called=False) as mock:
            route = mock.get(self.QUOTE_URL, params={"interval": "1d", "range": "1d"}).mock(
                return_value=httpx.Response(200, json=payload)
            )
            provider = YahooQuoteProvider(clock=FrozenClock(MOMENT))
            quote = await provider.get_quote("btc-usd")

        assert route.called
        assert quote is not None
        assert quote.symbol == "BTC-USD"
        assert quote.price.amount == Decimal("615000.0")
        assert quote.price.currency.code == "BRL"
        assert quote.source == "yahoo"
        assert quote.change_percent == Decimal("2.5000")
        assert quote.as_of == datetime.fromtimestamp(1748793600, tz=UTC)

    async def test_unknown_symbol_returns_none_on_404(self) -> None:
        with respx.mock(assert_all_called=False) as mock:
            mock.get(self.QUOTE_URL, params={"interval": "1d", "range": "1d"}).mock(
                return_value=httpx.Response(404, json={"chart": {"error": "not found"}})
            )
            provider = YahooQuoteProvider(clock=FrozenClock(MOMENT))
            assert await provider.get_quote("BTC-USD") is None

    async def test_history_parses_timestamps_and_skips_missing_closes(self) -> None:
        start, end = date(2026, 6, 1), date(2026, 6, 3)
        payload = {
            "chart": {
                "result": [
                    {
                        "meta": {"currency": "BRL"},
                        "timestamp": [
                            _epoch(start),
                            _epoch(date(2026, 6, 2)),
                            _epoch(end),
                        ],
                        "indicators": {"quote": [{"close": [600000.0, None, 610000.0]}]},
                    }
                ],
                "error": None,
            }
        }
        with respx.mock(assert_all_called=False) as mock:
            mock.get(
                self.QUOTE_URL,
                params={
                    "interval": "1d",
                    "period1": str(_epoch(start)),
                    "period2": str(_epoch(end)),
                },
            ).mock(return_value=httpx.Response(200, json=payload))
            provider = YahooQuoteProvider(clock=FrozenClock(MOMENT))
            points = await provider.get_history("BTC-USD", start=start, end=end)

        assert [point.date for point in points] == [start, end]
        assert [point.close.amount for point in points] == [
            Decimal("600000.0"),
            Decimal("610000.0"),
        ]


class TestSeedQuoteProvider:
    async def test_is_deterministic_and_uses_the_seed_table(self) -> None:
        provider = SeedQuoteProvider(FrozenClock(MOMENT))
        first = await provider.get_quote("PETR4")
        second = await provider.get_quote("PETR4")
        assert first == second
        assert first is not None
        assert first.price.amount == Decimal("38.72")
        assert first.source == "seed"
        assert first.as_of.tzinfo is UTC

    async def test_resolves_fx_and_tesouro_aliases(self) -> None:
        provider = SeedQuoteProvider(FrozenClock(MOMENT))
        fx = await provider.get_quote("USDBRL=X")
        tesouro = await provider.get_quote("TESOURO2029")
        assert fx is not None
        assert fx.price.amount == SEED_PRICES["USD/BRL"]
        assert tesouro is not None
        assert tesouro.price.amount == Decimal("15230.50")

    async def test_unknown_symbol_returns_none(self) -> None:
        provider = SeedQuoteProvider(FrozenClock(MOMENT))
        assert await provider.get_quote("NAOEXISTE") is None
        assert (
            await provider.get_history("NAOEXISTE", start=date(2026, 6, 1), end=date(2026, 6, 3))
            == []
        )

    async def test_history_is_a_deterministic_walk_anchored_on_the_price(self) -> None:
        provider = SeedQuoteProvider(FrozenClock(MOMENT))
        start, end = date(2026, 6, 1), date(2026, 6, 10)
        first = await provider.get_history("PETR4", start=start, end=end)
        second = await provider.get_history("PETR4", start=start, end=end)

        assert list(first) == list(second)
        assert len(first) == 10
        assert first[0].date == start
        assert first[-1].date == end
        assert first[-1].close.amount == Decimal("38.72")

    async def test_blue_chips_all_have_seed_prices(self) -> None:
        provider = SeedQuoteProvider(FrozenClock(MOMENT))
        for symbol in BLUE_CHIPS:
            assert await provider.get_quote(symbol) is not None


class TestSeedMacroProvider:
    async def test_series_and_latest_are_deterministic(self) -> None:
        provider = SeedMacroProvider(FrozenClock(MOMENT))
        start, end = date(2026, 6, 1), date(2026, 6, 5)
        first = await provider.get_series(MacroSeriesCode.SELIC, start=start, end=end)
        second = await provider.get_series(MacroSeriesCode.SELIC, start=start, end=end)
        assert list(first) == list(second)
        assert len(first) == 5
        assert isinstance(first[0], IndexPointView)

        latest_end = await provider.latest(MacroSeriesCode.IPCA)
        assert latest_end is not None
        assert latest_end.code == "ipca"

    async def test_inverted_range_returns_empty(self) -> None:
        provider = SeedMacroProvider(FrozenClock(MOMENT))
        points = await provider.get_series(
            MacroSeriesCode.CDI, start=date(2026, 6, 10), end=date(2026, 6, 1)
        )
        assert points == []


def test_seed_price_table_covers_the_spec() -> None:
    assert SEED_PRICES["PETR4"] == Decimal("38.72")
    assert SEED_PRICES["BTC"] == Decimal("615000.00")
    assert SEED_PRICES["ETH"] == Decimal("18500.00")
    assert SEED_PRICES["USD/BRL"] == Decimal("5.42")
    assert SEED_PRICES["TESOURO SELIC 2029"] == Decimal("15230.50")
