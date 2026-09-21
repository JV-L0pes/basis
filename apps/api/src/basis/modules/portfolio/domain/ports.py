"""Portfolio domain ports and the contracts published to other contexts."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from basis.kernel.application.pagination import decode_cursor, encode_cursor
from basis.kernel.domain.errors import ValidationError
from basis.modules.portfolio.domain.models import Portfolio
from basis.modules.portfolio.domain.value_objects import PortfolioStatus


@dataclass(frozen=True, slots=True)
class PortfolioCursor:
    """Position in the portfolio list (created_at DESC, id DESC)."""

    created_at: datetime
    id: UUID

    def encode(self) -> str:
        return encode_cursor({"created_at": self.created_at.isoformat(), "id": str(self.id)})

    @classmethod
    def decode(cls, raw: str) -> PortfolioCursor:
        payload = decode_cursor(raw)
        try:
            return cls(
                created_at=datetime.fromisoformat(payload["created_at"]),
                id=UUID(payload["id"]),
            )
        except (KeyError, ValueError) as exc:
            raise ValidationError("Malformed pagination cursor") from exc


class PortfolioRepository(Protocol):
    """Persistence port for the Portfolio aggregate."""

    async def get(self, portfolio_id: UUID) -> Portfolio | None: ...

    async def add(self, portfolio: Portfolio) -> None: ...

    async def update(self, portfolio: Portfolio) -> None: ...

    async def list_page(
        self,
        *,
        limit: int,
        cursor: PortfolioCursor | None = None,
        client_id: UUID | None = None,
        status: PortfolioStatus | None = None,
    ) -> tuple[Sequence[Portfolio], bool]: ...

    async def count_for_client(self, client_id: UUID) -> int: ...

    async def all_ids(self) -> Sequence[UUID]: ...


# ---------------------------------------------------------------------------
# Published contracts (consumed by the analytics context)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TargetWeight:
    asset_class: str
    weight_bps: int


@dataclass(frozen=True, slots=True)
class TransactionSnapshot:
    id: UUID
    symbol: str
    asset_class: str
    currency: str
    kind: str
    trade_date: date
    quantity: Decimal
    price: Decimal
    fees: Decimal


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    symbol: str
    asset_class: str
    currency: str
    quantity: Decimal
    average_cost: Decimal
    cost_basis: Decimal
    realized_gain: Decimal
    income: Decimal
    costs: Decimal


@dataclass(frozen=True, slots=True)
class PortfolioSnapshot:
    id: UUID
    client_id: UUID
    name: str
    base_currency: str
    status: str
    targets: tuple[TargetWeight, ...]
    positions: tuple[PositionSnapshot, ...]
    transactions: tuple[TransactionSnapshot, ...]
    created_at: datetime


class PortfolioReader(Protocol):
    """Published contract: read-only, fully-folded portfolio snapshots."""

    async def get_snapshot(self, portfolio_id: UUID) -> PortfolioSnapshot | None: ...

    async def list_snapshots(
        self, *, limit: int = 100, client_id: UUID | None = None
    ) -> Sequence[PortfolioSnapshot]: ...


__all__ = [
    "PortfolioCursor",
    "PortfolioReader",
    "PortfolioRepository",
    "PortfolioSnapshot",
    "PositionSnapshot",
    "TargetWeight",
    "TransactionSnapshot",
]
