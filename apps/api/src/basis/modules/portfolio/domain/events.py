"""Portfolio domain events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from basis.kernel.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioOpened(DomainEvent):
    name: ClassVar[str] = "portfolio.portfolio_opened"
    portfolio_id: UUID
    client_id: UUID
    portfolio_name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TransactionRecorded(DomainEvent):
    name: ClassVar[str] = "portfolio.transaction_recorded"
    portfolio_id: UUID
    transaction_id: UUID
    kind: str
    symbol: str


@dataclass(frozen=True, slots=True, kw_only=True)
class AllocationTargetsSet(DomainEvent):
    name: ClassVar[str] = "portfolio.allocation_targets_set"
    portfolio_id: UUID
    targets: int


@dataclass(frozen=True, slots=True, kw_only=True)
class PortfolioArchived(DomainEvent):
    name: ClassVar[str] = "portfolio.portfolio_archived"
    portfolio_id: UUID


__all__ = [
    "AllocationTargetsSet",
    "PortfolioArchived",
    "PortfolioOpened",
    "TransactionRecorded",
]
