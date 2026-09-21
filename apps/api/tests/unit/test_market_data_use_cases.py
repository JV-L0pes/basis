"""Unit tests for market-data use cases using in-memory doubles."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from basis.kernel.domain.assets import AssetClass
from basis.kernel.domain.clock import FrozenClock
from basis.kernel.domain.currency import BRL
from basis.kernel.domain.errors import NotFoundError, ValidationError
from basis.kernel.domain.money import Money
from basis.modules.market_data.application.use_cases import (
    GetInstrument,
    GetMacroSeries,
    GetMarketOverview,
    GetPriceHistory,
    GetQuote,
    GetQuotes,
    MacroSeriesQuery,
    PriceHistoryQuery,
    SearchInstruments,
    SearchInstrumentsQuery,
)
from basis.modules.market_data.domain.models import Instrument, PricePoint
from basis.modules.market_data.domain.ports import IndexPointView
from basis.modules.market_data.domain.value_objects import (
    MacroSeriesCode,
    TickerSymbol,
)
from tests.fakes import (
    InMemoryInstrumentCatalog,
    InMemoryInstrumentRepository,
    StubMacroProvider,
    StubQuoteProvider,
)

MOMENT = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
TODAY = date(2026, 6, 1)


def make_instrument(
    symbol: str,
    *,
    name: str | None = None,
    asset_class: AssetClass = AssetClass.EQUITY,
) -> Instrument:
    return Instrument.register(
        symbol=TickerSymbol(symbol),
        name=name or f"{symbol} Company",
        asset_class=asset_class,
        currency=BRL,
        clock=FrozenClock(MOMENT),
    )


class Harness:
    """Wires the market-data use cases against in-memory doubles."""

    def __init__(
        self,
        *,
        prices: dict[str, Decimal] | None = None,
        history: dict[str, list[PricePoint]] | None = None,
        series: dict[MacroSeriesCode, list[IndexPointView]] | None = None,
        failing_macro: set[MacroSeriesCode] | None = None,
        fail_quotes: bool = False,
        max_history_days: int = 365,
    ) -> None:
        self.clock = FrozenClock(MOMENT)
        self.instruments = InMemoryInstrumentRepository()
        self.catalog = InMemoryInstrumentCatalog(self.instruments)
        self.quotes = StubQuoteProvider(prices=prices, history=history, fail=fail_quotes)
        self.macro = StubMacroProvider(series=series, failing=failing_macro)
        self.search = SearchInstruments(instruments=self.instruments)
        self.get_instrument = GetInstrument(instruments=self.instruments)
        self.get_quote = GetQuote(catalog=self.catalog, quotes=self.quotes)
        self.get_quotes = GetQuotes(quotes=self.quotes)
        self.get_history = GetPriceHistory(
            catalog=self.catalog,
            quotes=self.quotes,
            clock=self.clock,
            max_history_days=max_history_days,
        )
        self.get_macro = GetMacroSeries(macro=self.macro, clock=self.clock)
        self.get_overview = GetMarketOverview(
            quotes=self.quotes, macro=self.macro, symbols=("PETR4", "VALE3", "XPTO3")
        )

    async def seed_catalogue(self) -> None:
        await self.instruments.add(make_instrument("PETR4", name="Petrobras"))
        await self.instruments.add(make_instrument("VALE3", name="Vale"))
        await self.instruments.add(
            make_instrument("BTC", name="Bitcoin", asset_class=AssetClass.CRYPTO)
        )


class TestSearchInstruments:
    async def test_returns_every_instrument_sorted_by_symbol(self) -> None:
        harness = Harness()
        await harness.seed_catalogue()
        page = await harness.search.execute(SearchInstrumentsQuery())
        assert [item.symbol for item in page.items] == ["BTC", "PETR4", "VALE3"]
        assert page.next_cursor is None
        assert page.has_more is False

    async def test_filters_by_query_on_symbol_and_name(self) -> None:
        harness = Harness()
        await harness.seed_catalogue()
        page = await harness.search.execute(SearchInstrumentsQuery(query="vale"))
        assert [item.symbol for item in page.items] == ["VALE3"]

    async def test_filters_by_asset_class(self) -> None:
        harness = Harness()
        await harness.seed_catalogue()
        page = await harness.search.execute(SearchInstrumentsQuery(asset_class=AssetClass.CRYPTO))
        assert [item.symbol for item in page.items] == ["BTC"]

    async def test_paginates_with_an_opaque_cursor(self) -> None:
        harness = Harness()
        await harness.seed_catalogue()
        first = await harness.search.execute(SearchInstrumentsQuery(limit=2))
        assert [item.symbol for item in first.items] == ["BTC", "PETR4"]
        assert first.next_cursor is not None

        second = await harness.search.execute(
            SearchInstrumentsQuery(limit=2, cursor=first.next_cursor)
        )
        assert [item.symbol for item in second.items] == ["VALE3"]
        assert second.next_cursor is None

    async def test_empty_catalogue_returns_empty_page(self) -> None:
        page = await Harness().search.execute(SearchInstrumentsQuery())
        assert list(page.items) == []


class TestGetInstrument:
    async def test_returns_view_for_known_symbol(self) -> None:
        harness = Harness()
        await harness.seed_catalogue()
        view = await harness.get_instrument.execute("petr4")
        assert view.symbol == "PETR4"
        assert view.asset_class is AssetClass.EQUITY
        assert view.currency == "BRL"

    async def test_unknown_symbol_raises(self) -> None:
        with pytest.raises(NotFoundError):
            await Harness().get_instrument.execute("XPTO3")


class TestGetQuote:
    async def test_returns_quote_from_the_provider(self) -> None:
        harness = Harness(prices={"PETR4": Decimal("38.72")})
        await harness.seed_catalogue()
        quote = await harness.get_quote.execute("PETR4")
        assert quote is not None
        assert quote.price.amount == Decimal("38.72")
        assert quote.source == "stub"

    async def test_missing_quote_returns_none(self) -> None:
        harness = Harness()
        await harness.seed_catalogue()
        assert await harness.get_quote.execute("PETR4") is None

    async def test_unknown_instrument_raises_not_found(self) -> None:
        harness = Harness(prices={"PETR4": Decimal("38.72")})
        with pytest.raises(NotFoundError):
            await harness.get_quote.execute("PETR4")


class TestGetQuotes:
    async def test_batch_omits_symbols_without_quotes(self) -> None:
        harness = Harness(prices={"PETR4": Decimal("38.72"), "VALE3": Decimal("61.45")})
        quotes = await harness.get_quotes.execute(["PETR4", "VALE3", "XPTO3"])
        assert set(quotes) == {"PETR4", "VALE3"}


class TestGetPriceHistory:
    async def test_defaults_to_the_last_ninety_days(self) -> None:
        harness = Harness(prices={"PETR4": Decimal("38.72")})
        await harness.seed_catalogue()
        await harness.get_history.execute(PriceHistoryQuery(symbol="PETR4"))
        symbol, start, end = harness.quotes.history_calls[0]
        assert symbol == "PETR4"
        assert end == TODAY
        assert start == TODAY - timedelta(days=90)

    async def test_clamps_the_window_to_max_history_days(self) -> None:
        harness = Harness(prices={"PETR4": Decimal("38.72")}, max_history_days=30)
        await harness.seed_catalogue()
        await harness.get_history.execute(
            PriceHistoryQuery(symbol="PETR4", start=date(2020, 1, 1), end=date(2026, 6, 1))
        )
        _, start, end = harness.quotes.history_calls[-1]
        assert start == date(2026, 5, 2)
        assert (end - start).days == 30

    async def test_returns_dtos_within_the_window(self) -> None:
        points = [
            PricePoint(date=date(2026, 5, 29), close=Money(Decimal("38.00"), BRL)),
            PricePoint(date=date(2026, 5, 30), close=Money(Decimal("38.50"), BRL)),
            PricePoint(date=date(2026, 5, 31), close=Money(Decimal("39.00"), BRL)),
        ]
        harness = Harness(prices={"PETR4": Decimal("38.72")}, history={"PETR4": points})
        await harness.seed_catalogue()
        result = await harness.get_history.execute(
            PriceHistoryQuery(symbol="PETR4", start=date(2026, 5, 29), end=date(2026, 5, 31))
        )
        assert [item.close for item in result] == [
            Decimal("38.00"),
            Decimal("38.50"),
            Decimal("39.00"),
        ]
        assert result[0].currency == "BRL"

    async def test_inverted_range_is_rejected(self) -> None:
        harness = Harness()
        await harness.seed_catalogue()
        with pytest.raises(ValidationError):
            await harness.get_history.execute(
                PriceHistoryQuery(symbol="PETR4", start=date(2026, 6, 2), end=date(2026, 6, 1))
            )

    async def test_unknown_instrument_raises(self) -> None:
        harness = Harness()
        with pytest.raises(NotFoundError):
            await harness.get_history.execute(PriceHistoryQuery(symbol="XPTO3"))


class TestGetMacroSeries:
    async def test_defaults_to_the_last_year(self) -> None:
        harness = Harness()
        await harness.get_macro.execute(MacroSeriesQuery(code=MacroSeriesCode.SELIC))
        code, start, end = harness.macro.series_calls[0]
        assert code is MacroSeriesCode.SELIC
        assert end == TODAY
        assert start == TODAY - timedelta(days=365)

    async def test_filters_points_to_the_window(self) -> None:
        points = [
            IndexPointView(code="selic", date=date(2026, 3, 1), value=Decimal("10.50")),
            IndexPointView(code="selic", date=date(2026, 6, 1), value=Decimal("10.75")),
        ]
        harness = Harness(series={MacroSeriesCode.SELIC: points})
        result = await harness.get_macro.execute(
            MacroSeriesQuery(
                code=MacroSeriesCode.SELIC,
                start=date(2026, 5, 1),
                end=date(2026, 6, 1),
            )
        )
        assert list(result) == [points[1]]

    async def test_inverted_range_is_rejected(self) -> None:
        harness = Harness()
        with pytest.raises(ValidationError):
            await harness.get_macro.execute(
                MacroSeriesQuery(
                    code=MacroSeriesCode.CDI,
                    start=date(2026, 6, 2),
                    end=date(2026, 6, 1),
                )
            )


class TestGetMarketOverview:
    async def test_combines_macro_latest_and_blue_chip_quotes(self) -> None:
        macro = {
            MacroSeriesCode.SELIC: [
                IndexPointView(code="selic", date=date(2026, 6, 1), value=Decimal("10.75"))
            ],
            MacroSeriesCode.IPCA: [
                IndexPointView(code="ipca", date=date(2026, 6, 1), value=Decimal("0.38"))
            ],
        }
        harness = Harness(
            prices={"PETR4": Decimal("38.72"), "VALE3": Decimal("61.45")}, series=macro
        )
        overview = await harness.get_overview.execute()

        assert [point.code for point in overview.macro] == ["selic", "ipca"]
        assert [quote.symbol for quote in overview.quotes] == ["PETR4", "VALE3"]
        assert harness.macro.latest_calls == list(MacroSeriesCode)

    async def test_omits_failing_macro_series_and_missing_quotes(self) -> None:
        macro = {
            MacroSeriesCode.SELIC: [
                IndexPointView(code="selic", date=date(2026, 6, 1), value=Decimal("10.75"))
            ]
        }
        harness = Harness(
            prices={"PETR4": Decimal("38.72")},
            series=macro,
            failing_macro={MacroSeriesCode.CDI},
        )
        overview = await harness.get_overview.execute()
        assert [point.code for point in overview.macro] == ["selic"]
        assert [quote.symbol for quote in overview.quotes] == ["PETR4"]

    async def test_stays_available_when_the_quote_provider_fails(self) -> None:
        harness = Harness(fail_quotes=True)
        overview = await harness.get_overview.execute()
        assert list(overview.quotes) == []
        assert list(overview.macro) == []
