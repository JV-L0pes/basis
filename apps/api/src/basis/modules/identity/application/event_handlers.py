"""Identity event handlers — the module's reaction to its own events.

In a modular monolith other bounded contexts subscribe here too; keeping the
wiring in one place makes the event contracts explicit.
"""

from __future__ import annotations

from basis.kernel.infrastructure.events import InProcessEventBus
from basis.logging import get_logger
from basis.modules.identity.domain.events import UserRegistered

logger = get_logger("identity.events")


async def _on_user_registered(event: UserRegistered) -> None:
    logger.info(
        "user_registered",
        user_id=str(event.user_id),
        email=event.email,
        role=event.role,
    )


def register_identity_handlers(bus: InProcessEventBus) -> None:
    """Subscribe identity handlers to the in-process bus."""
    bus.subscribe(UserRegistered, _on_user_registered)


__all__ = ["register_identity_handlers"]
