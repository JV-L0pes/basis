"""Entity and aggregate root bases (tactical DDD)."""

from __future__ import annotations

from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from basis.kernel.domain.events import DomainEvent


@dataclass(eq=False, slots=True)
class Entity[IdT]:
    """Base for identity-based objects.

    Subclasses are ``@dataclass(eq=False, slots=True)``; equality and hashing
    are identity based (never structural).
    """

    id: IdT

    def __eq__(self, other: object) -> bool:
        if other is self:
            return True
        if type(other) is not type(self):
            return NotImplemented
        return bool(self.id == other.id)

    def __hash__(self) -> int:
        return hash((type(self).__name__, self.id))

    def __repr__(self) -> str:
        return f"{type(self).__name__}(id={self.id!r})"


@dataclass(eq=False, slots=True)
class AggregateRoot[IdT](Entity[IdT], ABC):
    """An entity that is the consistency boundary and records domain events."""

    _events: list[DomainEvent] = field(init=False, default_factory=list, repr=False, compare=False)

    def record(self, event: DomainEvent) -> None:
        """Append a domain event to be published after the unit of work commits."""
        self._events.append(event)

    def pull_events(self) -> list[DomainEvent]:
        """Return recorded events and clear the buffer (call after commit)."""
        events, self._events = self._events, []
        return events

    @property
    def has_events(self) -> bool:
        return len(self._events) > 0


__all__ = ["AggregateRoot", "Entity"]
