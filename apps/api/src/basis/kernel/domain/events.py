"""Domain events and the in-process publisher port."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import ClassVar, Protocol, runtime_checkable
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent:
    """A fact that happened in the domain, expressed in the past tense."""

    name: ClassVar[str] = "domain_event"

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime

    def __str__(self) -> str:
        return f"{self.name}@{self.occurred_at.isoformat()}"


@runtime_checkable
class EventPublisher(Protocol):
    """Port for publishing domain events after a successful commit."""

    async def publish(self, events: Sequence[DomainEvent]) -> None: ...


EventHandler = Callable[[DomainEvent], Awaitable[None]]


__all__ = ["DomainEvent", "EventHandler", "EventPublisher"]
