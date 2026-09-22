"""HTTP schemas for the portfolio context."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from basis.kernel.domain.money import Money
from basis.kernel.infrastructure.http.schemas import decimal_str, money_str
from basis.modules.portfolio.application.dto import (
    PortfolioPage,
    PortfolioView,
    TargetWeightView,
    TransactionView,
)
from basis.modules.portfolio.domain.valuation import PortfolioValuation, PositionValuation


def money_amount(money: Money) -> str:
    return money_str(money)


class OpenPortfolioRequest(BaseModel):
    client_id: UUID
    name: str = Field(min_length=2, max_length=80)
    base_currency: str = Field(default="BRL", min_length=3, max_length=5)


class RenamePortfolioRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)


class TargetWeightRequest(BaseModel):
    asset_class: Literal[
        "equity",
        "fixed_income",
        "fund",
        "etf",
        "real_estate",
        "crypto",
        "cash",
        "commodity",
        "other",
    ]
    weight_bps: int = Field(ge=0, le=10_000)


class SetTargetsRequest(BaseModel):
    targets: list[TargetWeightRequest] = Field(default_factory=list)


class RecordTransactionRequest(BaseModel):
    symbol: str = Field(min_length=2, max_length=15)
    kind: Literal["buy", "sell", "dividend", "interest", "fee"]
    trade_date: date
    quantity: Decimal = Field(gt=0, description="Quantity traded")
    price: Decimal = Field(ge=0, description="Unit price (or cash amount for income/expense)")
    fees: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=280)


class TargetWeightResponse(BaseModel):
    asset_class: str
    weight_bps: int
    weight_percent: float

    @classmethod
    def from_view(cls, view: TargetWeightView) -> TargetWeightResponse:
        return cls(
            asset_class=view.asset_class,
            weight_bps=view.weight_bps,
            weight_percent=float(view.weight_percent),
        )


class PositionValuationResponse(BaseModel):
    symbol: str
    asset_class: str
    currency: str
    quantity: str
    average_cost: str
    cost_basis: str
    market_price: str | None
    market_value: str | None
    unrealized_gain: str | None
    unrealized_gain_percent: float | None
    realized_gain: str
    income: str
    costs: str
    weight: float | None

    @classmethod
    def from_valuation(cls, valuation: PositionValuation) -> PositionValuationResponse:
        return cls(
            symbol=valuation.instrument.symbol,
            asset_class=str(valuation.instrument.asset_class),
            currency=valuation.instrument.currency.code,
            quantity=decimal_str(valuation.quantity),
            average_cost=money_amount(valuation.average_cost),
            cost_basis=money_amount(valuation.cost_basis),
            market_price=(
                money_amount(valuation.market_price) if valuation.market_price else None
            ),
            market_value=(
                money_amount(valuation.market_value) if valuation.market_value else None
            ),
            unrealized_gain=(
                money_amount(valuation.unrealized_gain) if valuation.unrealized_gain else None
            ),
            unrealized_gain_percent=(
                float(valuation.unrealized_gain_percent)
                if valuation.unrealized_gain_percent is not None
                else None
            ),
            realized_gain=money_amount(valuation.realized_gain),
            income=money_amount(valuation.income),
            costs=money_amount(valuation.costs),
            weight=float(valuation.weight) if valuation.weight is not None else None,
        )


class PortfolioValuationResponse(BaseModel):
    base_currency: str
    invested: str
    market_value: str
    unrealized_gain: str
    realized_gain: str
    income: str
    costs: str
    net_result: str
    return_percent: float | None
    unpriced_symbols: list[str]
    positions: list[PositionValuationResponse]

    @classmethod
    def from_valuation(cls, valuation: PortfolioValuation) -> PortfolioValuationResponse:
        return cls(
            base_currency=valuation.base_currency.code,
            invested=money_amount(valuation.invested),
            market_value=money_amount(valuation.market_value),
            unrealized_gain=money_amount(valuation.unrealized_gain),
            realized_gain=money_amount(valuation.realized_gain),
            income=money_amount(valuation.income),
            costs=money_amount(valuation.costs),
            net_result=money_amount(valuation.net_result),
            return_percent=(
                float(valuation.return_percent) if valuation.return_percent is not None else None
            ),
            unpriced_symbols=list(valuation.unpriced_symbols),
            positions=[
                PositionValuationResponse.from_valuation(position)
                for position in valuation.positions
            ],
        )


class PortfolioResponse(BaseModel):
    id: UUID
    client_id: UUID
    name: str
    base_currency: str
    status: str
    targets: list[TargetWeightResponse]
    position_count: int
    transaction_count: int
    created_at: datetime
    updated_at: datetime
    valuation: PortfolioValuationResponse | None

    @classmethod
    def from_view(cls, view: PortfolioView) -> PortfolioResponse:
        return cls(
            id=view.id,
            client_id=view.client_id,
            name=view.name,
            base_currency=view.base_currency,
            status=view.status,
            targets=[TargetWeightResponse.from_view(target) for target in view.targets],
            position_count=view.position_count,
            transaction_count=view.transaction_count,
            created_at=view.created_at,
            updated_at=view.updated_at,
            valuation=(
                PortfolioValuationResponse.from_valuation(view.valuation)
                if view.valuation is not None
                else None
            ),
        )


class PortfolioListResponse(BaseModel):
    items: list[PortfolioResponse]
    next_cursor: str | None = None

    @classmethod
    def from_page(cls, page: PortfolioPage) -> PortfolioListResponse:
        return cls(
            items=[PortfolioResponse.from_view(item) for item in page.items],
            next_cursor=page.next_cursor,
        )


class TransactionResponse(BaseModel):
    id: UUID
    symbol: str
    asset_class: str
    kind: str
    trade_date: date
    quantity: str
    price: str
    fees: str
    gross_value: str
    notes: str | None

    @classmethod
    def from_view(cls, view: TransactionView) -> TransactionResponse:
        return cls(
            id=view.id,
            symbol=view.symbol,
            asset_class=view.asset_class,
            kind=view.kind,
            trade_date=view.trade_date,
            quantity=decimal_str(view.quantity),
            price=money_amount(view.price),
            fees=money_amount(view.fees),
            gross_value=money_amount(view.gross_value),
            notes=view.notes,
        )


__all__ = [
    "OpenPortfolioRequest",
    "PortfolioListResponse",
    "PortfolioResponse",
    "PortfolioValuationResponse",
    "RecordTransactionRequest",
    "RenamePortfolioRequest",
    "SetTargetsRequest",
    "TargetWeightResponse",
    "TransactionResponse",
]
