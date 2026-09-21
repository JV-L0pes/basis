"""HTTP schemas for the clients context."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field

from basis.modules.clients.application.dto import ClientPage, ClientView

NameField = Annotated[str, Field(min_length=2, max_length=120)]
EmailField = Annotated[str, Field(min_length=3, max_length=254)]


class RegisterClientRequest(BaseModel):
    name: NameField
    email: EmailField
    tax_id: str = Field(
        min_length=11,
        max_length=18,
        description="CPF (11 digits) or CNPJ (14 digits); punctuation is accepted",
    )
    notes: str | None = Field(default=None, max_length=500)
    suitability_answers: list[int] | None = Field(
        default=None,
        description="5 to 10 answers, each between 0 and 4",
    )


class UpdateClientRequest(BaseModel):
    name: NameField | None = None
    email: EmailField | None = None
    notes: str | None = Field(default=None, max_length=500)


class AssessSuitabilityRequest(BaseModel):
    answers: list[int] = Field(min_length=5, max_length=10)


class SuitabilityResponse(BaseModel):
    """Outcome of a suitability questionnaire."""

    score: int
    profile: str

    @classmethod
    def from_view(cls, view: ClientView) -> SuitabilityResponse:
        return cls(score=view.suitability_score, profile=view.suitability)


class ClientResponse(BaseModel):
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
    def from_view(cls, view: ClientView) -> ClientResponse:
        return cls(
            id=view.id,
            name=view.name,
            email=view.email,
            tax_id_masked=view.tax_id_masked,
            tax_id_kind=view.tax_id_kind,
            suitability=view.suitability,
            suitability_score=view.suitability_score,
            status=view.status,
            notes=view.notes,
            created_at=view.created_at,
            updated_at=view.updated_at,
        )


class ClientListResponse(BaseModel):
    items: list[ClientResponse]
    next_cursor: str | None = None

    @classmethod
    def from_page(cls, page: ClientPage) -> ClientListResponse:
        return cls(
            items=[ClientResponse.from_view(item) for item in page.items],
            next_cursor=page.next_cursor,
        )


__all__ = [
    "AssessSuitabilityRequest",
    "ClientListResponse",
    "ClientResponse",
    "RegisterClientRequest",
    "SuitabilityResponse",
    "UpdateClientRequest",
]
