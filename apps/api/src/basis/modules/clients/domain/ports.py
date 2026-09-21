"""Clients domain ports, including the contract published to other contexts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from basis.kernel.application.pagination import decode_cursor, encode_cursor
from basis.kernel.domain.errors import ValidationError
from basis.modules.clients.domain.models import Client
from basis.modules.clients.domain.value_objects import ClientStatus, TaxId


@dataclass(frozen=True, slots=True)
class ClientCursor:
    """Position in the client list (created_at DESC, id DESC)."""

    created_at: datetime
    id: UUID

    def encode(self) -> str:
        return encode_cursor({"created_at": self.created_at.isoformat(), "id": str(self.id)})

    @classmethod
    def decode(cls, raw: str) -> ClientCursor:
        payload = decode_cursor(raw)
        try:
            return cls(
                created_at=datetime.fromisoformat(payload["created_at"]),
                id=UUID(payload["id"]),
            )
        except (KeyError, ValueError) as exc:
            raise ValidationError("Malformed pagination cursor") from exc


@dataclass(frozen=True, slots=True)
class ClientSummary:
    """Minimal client data other bounded contexts are allowed to see."""

    id: UUID
    name: str
    status: str
    suitability: str


class ClientRepository(Protocol):
    """Persistence port for the Client aggregate."""

    async def get(self, client_id: UUID) -> Client | None: ...

    async def get_by_tax_id(self, tax_id: TaxId) -> Client | None: ...

    async def add(self, client: Client) -> None: ...

    async def update(self, client: Client) -> None: ...

    async def list_page(
        self,
        *,
        limit: int,
        cursor: ClientCursor | None = None,
        query: str | None = None,
        status: ClientStatus | None = None,
    ) -> tuple[Sequence[Client], bool]: ...

    async def count_by_status(self) -> Mapping[ClientStatus, int]: ...


class ClientDirectory(Protocol):
    """Published contract: read-only access to client summaries."""

    async def get_client_summary(self, client_id: UUID) -> ClientSummary | None: ...

    async def require_client(self, client_id: UUID) -> ClientSummary: ...


__all__ = ["ClientCursor", "ClientDirectory", "ClientRepository", "ClientSummary"]
