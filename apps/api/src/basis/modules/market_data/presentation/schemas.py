"""HTTP schemas for the market data context."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from basis.kernel.infrastructure.http.schemas import decimal_str, money_str
from basis.modules.market_data.application.dto import (
    InstrumentPage,
    InstrumentView,
    MarketOverview,
    PricePointDTO,
)
from basis.modules.market_data.domain.ports import IndexPointView, QuoteView
from basis.modules.market_data.domain.value_objects import MacroSeriesCode


class InstrumentResponse(BaseModel):
    id: str
    symbol: str
    name: str
    asset_class: str
    currency: str
    mic: str | None
    isin: str | None
    cfi: str | None
    is_active: bool

    @classmethod
    def from_view(cls, view: InstrumentView) -> InstrumentResponse:
        return cls(
            id=str(view.id),
            symbol=view.symbol,
            name=view.name,
            asset_class=str(view.asset_class),
            currency=view.currency,
            mic=view.mic,
            isin=view.isin,
            cfi=view.cfi,
            is_active=view.is_active,
        )


class InstrumentListResponse(BaseModel):
    items: list[InstrumentResponse]
    next_cursor: str | None = None

    @classmethod
    def from_page(cls, page: InstrumentPage) -> InstrumentListResponse:
        return cls(
            items=[InstrumentResponse.from_view(item) for item in page.items],
            next_cursor=page.next_cursor,
        )


class QuoteResponse(BaseModel):
    """A quote as served to clients: exact decimals serialised as strings."""

    symbol: str
    price: str
    currency: str
    as_of: datetime
    source: str
    change_percent: float | None = None

    @classmethod
    def from_quote(cls, quote: QuoteView) -> QuoteResponse:
        return cls(
            symbol=quote.symbol,
            price=money_str(quote.price),
            currency=quote.price.currency.code,
            as_of=quote.as_of,
            source=quote.source,
            change_percent=(
                float(quote.change_percent) if quote.change_percent is not None else None
            ),
        )


class PricePointResponse(BaseModel):
    date: date
    close: str
    currency: str

    @classmethod
    def from_dto(cls, point: PricePointDTO) -> PricePointResponse:
        return cls(date=point.date, close=decimal_str(point.close), currency=point.currency)


class MacroPointResponse(BaseModel):
    code: str
    label: str
    unit: str
    date: date
    value: str

    @classmethod
    def from_point(cls, point: IndexPointView) -> MacroPointResponse:
        try:
            code = MacroSeriesCode.parse(point.code)
        except ValueError:  # pragma: no cover - defensive
            return cls(
                code=point.code,
                label=point.code,
                unit="",
                date=point.date,
                value=decimal_str(point.value),
            )
        return cls(
            code=point.code,
            label=code.label,
            unit=code.unit,
            date=point.date,
            value=decimal_str(point.value),
        )


class MarketOverviewResponse(BaseModel):
    macro: list[MacroPointResponse]
    quotes: list[QuoteResponse]
    gainers: list[QuoteResponse]
    losers: list[QuoteResponse]

    @classmethod
    def from_overview(cls, overview: MarketOverview) -> MarketOverviewResponse:
        return cls(
            macro=[MacroPointResponse.from_point(point) for point in overview.macro],
            quotes=[QuoteResponse.from_quote(quote) for quote in overview.quotes],
            gainers=[QuoteResponse.from_quote(quote) for quote in overview.gainers],
            losers=[QuoteResponse.from_quote(quote) for quote in overview.losers],
        )


__all__ = [
    "InstrumentListResponse",
    "InstrumentResponse",
    "MacroPointResponse",
    "MarketOverviewResponse",
    "PricePointResponse",
    "QuoteResponse",
]
