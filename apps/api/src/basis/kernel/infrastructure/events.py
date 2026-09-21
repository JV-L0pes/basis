"""In-process domain event bus.

Handlers are registered at application startup (see ``basis.main``). In a
modular monolith this is how one bounded context reacts to another context's
events without importing its internals.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar

from basis.kernel.domain.events import DomainEvent
from basis.logging import get_logger

E = TypeVar("E", bound=DomainEvent)
Handler = Callable[[DomainEvent], Awaitable[None]]

logger = get_logger("kernel.events")


class InProcessEventBus:
    """Dispatches domain events to subscribed async handlers."""

    __slots__ = ("_handlers",)

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type[E], handler: Callable[[E], Awaitable[None]]) -> None:
        """Register ``handler`` for ``event_type``."""

        async def adapter(event: DomainEvent) -> None:
            if isinstance(event, event_type):
                await handler(event)

        self._handlers[event_type].append(adapter)

    def handlers_for(self, event_type: type[DomainEvent]) -> Sequence[Handler]:
        return tuple(self._handlers.get(event_type, ()))

    async def publish(self, events: Sequence[DomainEvent]) -> None:
        """Dispatch events in order. A failing handler never breaks the caller."""
        for event in events:
            for handler in self._handlers.get(type(event), ()):
                try:
                    await handler(event)
                except Exception:
                    # Handlers must never break the publisher.
                    logger.exception(
                        "domain_event_handler_failed",
                        domain_event=event.name,
                        handler=getattr(handler, "__qualname__", repr(handler)),
                    )


__all__ = ["Handler", "InProcessEventBus"]
