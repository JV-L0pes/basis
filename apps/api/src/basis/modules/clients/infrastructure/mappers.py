"""Mapping between persistence rows and domain objects (clients context)."""

from __future__ import annotations

from basis.modules.clients.domain.models import Client
from basis.modules.clients.domain.value_objects import (
    ClientStatus,
    ContactEmail,
    PersonName,
    SuitabilityProfile,
    TaxId,
)
from basis.modules.clients.infrastructure.models import ClientRow


def client_to_domain(row: ClientRow) -> Client:
    return Client(
        id=row.id,
        name=PersonName(row.name),
        email=ContactEmail(row.email),
        tax_id=TaxId(row.tax_id),
        suitability=SuitabilityProfile(row.suitability),
        suitability_score=row.suitability_score,
        status=ClientStatus(row.status),
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def client_to_row(client: Client) -> ClientRow:
    return ClientRow(
        id=client.id,
        name=client.name.value,
        email=client.email.value,
        tax_id=client.tax_id.value,
        tax_id_kind=str(client.tax_id.kind),
        suitability=str(client.suitability),
        suitability_score=client.suitability_score,
        status=str(client.status),
        notes=client.notes,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


def apply_client(client: Client, row: ClientRow) -> None:
    row.name = client.name.value
    row.email = client.email.value
    row.tax_id = client.tax_id.value
    row.tax_id_kind = str(client.tax_id.kind)
    row.suitability = str(client.suitability)
    row.suitability_score = client.suitability_score
    row.status = str(client.status)
    row.notes = client.notes
    row.updated_at = client.updated_at


__all__ = ["apply_client", "client_to_domain", "client_to_row"]
