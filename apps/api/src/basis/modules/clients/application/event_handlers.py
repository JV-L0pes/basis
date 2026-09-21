"""Clients event handlers."""

from __future__ import annotations

from basis.kernel.infrastructure.events import InProcessEventBus
from basis.logging import get_logger
from basis.modules.clients.domain.events import ClientArchived, ClientRegistered

logger = get_logger("clients.events")


async def _on_client_registered(event: ClientRegistered) -> None:
    logger.info(
        "client_registered",
        client_id=str(event.client_id),
        suitability=event.suitability,
    )


async def _on_client_archived(event: ClientArchived) -> None:
    logger.info("client_archived", client_id=str(event.client_id))


def register_clients_handlers(bus: InProcessEventBus) -> None:
    """Subscribe clients handlers to the in-process bus."""
    bus.subscribe(ClientRegistered, _on_client_registered)
    bus.subscribe(ClientArchived, _on_client_archived)


__all__ = ["register_clients_handlers"]
