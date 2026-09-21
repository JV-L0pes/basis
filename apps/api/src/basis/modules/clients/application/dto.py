"""Read models (DTOs) for the clients context."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from basis.modules.clients.domain.models import Client


@dataclass(frozen=True, slots=True)
class ClientView:
    """Public representation of a client. The tax id is always masked."""

    id: UUID
    name: str
    email: str
    tax_id_masked: str
    tax_id_kind: str
    suitability: str
    suitability_score: int
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, client: Client) -> ClientView:
        return cls(
            id=client.id,
            name=client.name.value,
            email=client.email.value,
            tax_id_masked=client.tax_id.masked,
            tax_id_kind=str(client.tax_id.kind),
            suitability=str(client.suitability),
            suitability_score=client.suitability_score,
            status=str(client.status),
            notes=client.notes,
            created_at=client.created_at,
            updated_at=client.updated_at,
        )

    @classmethod
    def from_entities(cls, clients: Iterable[Client]) -> list[ClientView]:
        return [cls.from_entity(client) for client in clients]


@dataclass(frozen=True, slots=True)
class ClientPage:
    """A keyset page of clients."""

    items: list[ClientView]
    next_cursor: str | None = None

    @property
    def has_more(self) -> bool:
        return self.next_cursor is not None


__all__ = ["ClientPage", "ClientView"]
