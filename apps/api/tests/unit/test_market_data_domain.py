"""Unit tests for the market-data domain value objects and aggregates."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from basis.kernel.domain.assets import AssetClass
from basis.kernel.domain.clock import FrozenClock
from basis.kernel.domain.currency import BRL
from basis.kernel.domain.errors import ValidationError
from basis.kernel.domain.money import Money
from basis.modules.market_data.domain.events import (
    InstrumentDeactivated,
    InstrumentRegistered,
)
from basis.modules.market_data.domain.models import (
    Instrument,
    MacroPoint,
    PricePoint,
    Quote,
)
from basis.modules.market_data.domain.value_objects import (
    CfiCode,
    Isin,
    MacroSeriesCode,
    Mic,
    QuoteSource,
    TickerSymbol,
)

MOMENT = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)


class TestMic:
    def test_accepts_plain_and_segment_codes(self) -> None:
        assert Mic("BVMF").value == "BVMF"
        assert Mic("xnys-arca").value == "XNYS-ARCA"

    @pytest.mark.parametrize("value", ["", "BVM", "BVMF!ABC", "BVMF-AR", "1BVF"])
    def test_rejects_malformed_codes(self, value: str) -> None:
        with pytest.raises(ValidationError):
            Mic(value)


class TestIsin:
    def test_accepts_valid_isin_with_luhn_check_digit(self) -> None:
        isin = Isin("brpetracnpr6")
        assert isin.value == "BRPETRACNPR6"
        assert isin.country == "BR"

    def test_rejects_invalid_check_digit(self) -> None:
        with pytest.raises(ValidationError, match="check digit"):
            Isin("BRPETRACNPR7")

    @pytest.mark.parametrize(
        "value", ["BRPETRACNPR", "BRPETRACNPR67", "1RPETRACNPR6", "BRPETRACNPRX"]
    )
    def test_rejects_malformed_isins(self, value: str) -> None:
        with pytest.raises(ValidationError):
            Isin(value)


class TestCfiCode:
    def test_accepts_six_uppercase_letters(self) -> None:
        cfi = CfiCode("esvufr")
        assert cfi.value == "ESVUFR"
        assert cfi.category == "E"

    @pytest.mark.parametrize("value", ["ESVUF", "ESVUFR1", "esvuf"])
    def test_rejects_malformed_codes(self, value: str) -> None:
        with pytest.raises(ValidationError):
            CfiCode(value)


class TestTickerSymbol:
    @pytest.mark.parametrize(
        "value",
        ["PETR4", "IGUATEMI11", "VALE3", "BTC", "ETH-USD", "USDBRL=X"],
    )
    def test_accepts_b3_crypto_and_fx_symbols(self, value: str) -> None:
        assert TickerSymbol(value).value == value

    def test_normalizes_case_and_whitespace(self) -> None:
        assert TickerSymbol("  petr4 ").value == "PETR4"

    @pytest.mark.parametrize("value", ["", "A", "PE TR4", "PETR4!", "ABCDEFGHIJKLMNOP"])
    def test_rejects_malformed_symbols(self, value: str) -> None:
        with pytest.raises(ValidationError):
            TickerSymbol(value)


class TestQuote:
    def _money(self, amount: str = "38.72") -> Money:
        return Money(Decimal(amount), BRL)

    def test_accepts_aware_utc_quote(self) -> None:
        quote = Quote(
            instrument_id=uuid4(),
            symbol=TickerSymbol("PETR4"),
            price=self._money(),
            as_of=MOMENT,
            source=QuoteSource.SEED,
        )
        assert quote.change_percent is None
        assert quote.source is QuoteSource.SEED

    def test_zero_price_is_allowed(self) -> None:
        quote = Quote(
            instrument_id=uuid4(),
            symbol=TickerSymbol("PETR4"),
            price=self._money("0"),
            as_of=MOMENT,
            source=QuoteSource.BRAPI,
            change_percent=Decimal("-1.25"),
        )
        assert quote.price.amount == Decimal("0")

    def test_rejects_naive_timestamp(self) -> None:
        with pytest.raises(ValidationError, match="timezone-aware"):
            Quote(
                instrument_id=uuid4(),
                symbol=TickerSymbol("PETR4"),
                price=self._money(),
                as_of=datetime(2026, 6, 1, 10, 0),
                source=QuoteSource.SEED,
            )

    def test_rejects_non_utc_timestamp(self) -> None:
        with pytest.raises(ValidationError, match="timezone-aware"):
            Quote(
                instrument_id=uuid4(),
                symbol=TickerSymbol("PETR4"),
                price=self._money(),
                as_of=datetime(2026, 6, 1, 10, 0, tzinfo=timezone(timedelta(hours=-3))),
                source=QuoteSource.SEED,
            )

    def test_rejects_negative_price(self) -> None:
        with pytest.raises(ValidationError, match="negative"):
            Quote(
                instrument_id=uuid4(),
                symbol=TickerSymbol("PETR4"),
                price=self._money("-1.00"),
                as_of=MOMENT,
                source=QuoteSource.SEED,
            )


class TestInstrument:
    def _register(self, clock: FrozenClock | None = None) -> Instrument:
        return Instrument.register(
            symbol=TickerSymbol("PETR4"),
            name="  Petrobras   PN  ",
            asset_class=AssetClass.EQUITY,
            currency=BRL,
            mic=Mic("BVMF"),
            isin=Isin("BRPETRACNPR6"),
            cfi=CfiCode("ESVUFR"),
            clock=clock or FrozenClock(MOMENT),
        )

    def test_register_records_event_and_normalizes_name(self) -> None:
        instrument = self._register()
        assert instrument.name == "Petrobras PN"
        assert instrument.is_active is True
        events = instrument.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, InstrumentRegistered)
        assert event.symbol == "PETR4"
        assert event.instrument_id == instrument.id

    def test_register_rejects_short_name(self) -> None:
        with pytest.raises(ValidationError):
            Instrument.register(
                symbol=TickerSymbol("PETR4"),
                name="P",
                asset_class=AssetClass.EQUITY,
                currency=BRL,
                clock=FrozenClock(MOMENT),
            )

    def test_rename_updates_timestamp(self) -> None:
        clock = FrozenClock(MOMENT)
        instrument = self._register(clock)
        clock.advance(timedelta(hours=1))
        instrument.rename("Petrobras PN Renamed", clock=clock)
        assert instrument.name == "Petrobras PN Renamed"
        assert instrument.updated_at == MOMENT + timedelta(hours=1)

    def test_deactivate_is_idempotent_and_records_event_once(self) -> None:
        clock = FrozenClock(MOMENT)
        instrument = self._register(clock)
        instrument.pull_events()
        instrument.deactivate(clock=clock)
        instrument.deactivate(clock=clock)
        events = instrument.pull_events()
        assert instrument.is_active is False
        assert len(events) == 1
        assert isinstance(events[0], InstrumentDeactivated)


class TestPointValueObjects:
    def test_price_point_holds_date_and_money(self) -> None:
        point = PricePoint(date=date(2026, 6, 1), close=Money(Decimal("38.72"), BRL))
        assert point.close.amount == Decimal("38.72")

    def test_macro_point_holds_series_metadata(self) -> None:
        point = MacroPoint(
            code=MacroSeriesCode.SELIC, date=date(2026, 6, 1), value=Decimal("10.75")
        )
        assert point.code.bcb_sgs_id == 11


class TestMacroSeriesCode:
    @pytest.mark.parametrize(
        ("code", "sgs_id", "label", "unit"),
        [
            (MacroSeriesCode.SELIC, 11, "SELIC", "% a.a."),
            (MacroSeriesCode.CDI, 12, "CDI", "% a.m."),
            (MacroSeriesCode.IPCA, 433, "IPCA", "% a.m."),
            (MacroSeriesCode.USD_BRL, 1, "USD/BRL", "BRL"),
        ],
    )
    def test_exposes_bcb_metadata(
        self, code: MacroSeriesCode, sgs_id: int, label: str, unit: str
    ) -> None:
        assert code.bcb_sgs_id == sgs_id
        assert code.label == label
        assert code.unit == unit

    def test_parse_accepts_api_codes(self) -> None:
        assert MacroSeriesCode.parse("SELIC") is MacroSeriesCode.SELIC
        assert MacroSeriesCode.parse(" usd_brl ") is MacroSeriesCode.USD_BRL

    def test_parse_rejects_unknown_codes(self) -> None:
        with pytest.raises(ValidationError, match="Unknown macro"):
            MacroSeriesCode.parse("desconhecido")


class TestQuoteSource:
    def test_source_values_are_lowercase_slugs(self) -> None:
        assert QuoteSource.BRAPI.value == "brapi"
        assert QuoteSource.BCB.value == "bcb"
        assert QuoteSource.YAHOO.value == "yahoo"
        assert QuoteSource.SEED.value == "seed"
