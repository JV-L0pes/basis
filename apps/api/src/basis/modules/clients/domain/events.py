"""Clients domain events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from basis.kernel.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientRegistered(DomainEvent):
    name: ClassVar[str] = "clients.client_registered"
    client_id: UUID
    client_name: str
    tax_id_masked: str
    suitability: str
    suitability_score: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientSuitabilityAssessed(DomainEvent):
    name: ClassVar[str] = "clients.client_suitability_assessed"
    client_id: UUID
    suitability: str
    score: int


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientArchived(DomainEvent):
    name: ClassVar[str] = "clients.client_archived"
    client_id: UUID


__all__ = [
    "ClientArchived",
    "ClientRegistered",
    "ClientSuitabilityAssessed",
]
