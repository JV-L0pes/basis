"""The Client aggregate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Final
from uuid import UUID

from basis.kernel.domain.clock import Clock
from basis.kernel.domain.entity import AggregateRoot
from basis.kernel.domain.errors import InvariantViolationError, ValidationError
from basis.kernel.domain.identifiers import new_id
from basis.modules.clients.domain.events import (
    ClientArchived,
    ClientRegistered,
    ClientSuitabilityAssessed,
)
from basis.modules.clients.domain.value_objects import (
    NOTES_MAX_LENGTH,
    ClientStatus,
    ContactEmail,
    PersonName,
    SuitabilityAssessment,
    SuitabilityProfile,
    TaxId,
)


class _Unset(Enum):
    """Sentinel distinguishing "field not provided" from "clear the field"."""

    TOKEN = "unset"  # noqa: S105 — not a credential


UNSET: Final = _Unset.TOKEN


@dataclass(eq=False, slots=True)
class Client(AggregateRoot[UUID]):
    """An investor whose portfolios are managed on the platform."""

    name: PersonName
    email: ContactEmail
    tax_id: TaxId
    suitability: SuitabilityProfile
    suitability_score: int
    status: ClientStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime

    # -- factories --------------------------------------------------------
    @classmethod
    def register(
        cls,
        *,
        name: PersonName,
        email: ContactEmail,
        tax_id: TaxId,
        assessment: SuitabilityAssessment,
        notes: str | None,
        clock: Clock,
    ) -> Client:
        moment = clock.now()
        client = cls(
            id=new_id(),
            name=name,
            email=email,
            tax_id=tax_id,
            suitability=assessment.profile,
            suitability_score=assessment.score,
            status=ClientStatus.ACTIVE,
            notes=_validate_notes(notes),
            created_at=moment,
            updated_at=moment,
        )
        client.record(
            ClientRegistered(
                occurred_at=moment,
                client_id=client.id,
                client_name=name.value,
                tax_id_masked=tax_id.masked,
                suitability=str(client.suitability),
                suitability_score=client.suitability_score,
            )
        )
        return client

    # -- commands ---------------------------------------------------------
    def update_details(
        self,
        *,
        name: PersonName | None = None,
        email: ContactEmail | None = None,
        notes: str | _Unset | None = UNSET,
        clock: Clock,
    ) -> None:
        """Update contact details. Archived clients are immutable."""
        self._ensure_active("updated")
        if name is not None:
            self.name = name
        if email is not None:
            self.email = email
        if not isinstance(notes, _Unset):
            self.notes = _validate_notes(notes)
        self.updated_at = clock.now()

    def assess_suitability(self, assessment: SuitabilityAssessment, *, clock: Clock) -> None:
        """Replace the stored risk profile after a new questionnaire."""
        self._ensure_active("reassessed")
        moment = clock.now()
        self.suitability = assessment.profile
        self.suitability_score = assessment.score
        self.updated_at = moment
        self.record(
            ClientSuitabilityAssessed(
                occurred_at=moment,
                client_id=self.id,
                suitability=str(self.suitability),
                score=self.suitability_score,
            )
        )

    def archive(self, *, clock: Clock) -> None:
        """Archive the client. Idempotent."""
        if self.status is ClientStatus.ARCHIVED:
            return
        moment = clock.now()
        self.status = ClientStatus.ARCHIVED
        self.updated_at = moment
        self.record(ClientArchived(occurred_at=moment, client_id=self.id))

    def reactivate(self, *, clock: Clock) -> None:
        """Bring an archived client back to active. Idempotent."""
        if self.status is ClientStatus.ACTIVE:
            return
        self.status = ClientStatus.ACTIVE
        self.updated_at = clock.now()

    # -- helpers ----------------------------------------------------------
    @property
    def is_active(self) -> bool:
        return self.status is ClientStatus.ACTIVE

    def _ensure_active(self, action: str) -> None:
        if self.status is ClientStatus.ARCHIVED:
            raise InvariantViolationError(f"archived clients cannot be {action}")


def _validate_notes(notes: str | None) -> str | None:
    if notes is None:
        return None
    normalized = notes.strip()
    if not normalized:
        return None
    if len(normalized) > NOTES_MAX_LENGTH:
        raise ValidationError(
            f"Notes must be at most {NOTES_MAX_LENGTH} characters",
            details={"length": len(normalized)},
        )
    return normalized


__all__ = ["UNSET", "Client"]
