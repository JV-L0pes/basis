"""Market data event handlers."""

from __future__ import annotations

from basis.kernel.infrastructure.events import InProcessEventBus
from basis.logging import get_logger
from basis.modules.market_data.domain.events import InstrumentRegistered

logger = get_logger("market_data.events")


async def _on_instrument_registered(event: InstrumentRegistered) -> None:
    logger.debug(
        "instrument_registered",
        instrument_id=str(event.instrument_id),
        symbol=event.symbol,
        asset_class=event.asset_class,
    )


def register_market_data_handlers(bus: InProcessEventBus) -> None:
    """Subscribe market data handlers to the in-process bus."""
    bus.subscribe(InstrumentRegistered, _on_instrument_registered)


__all__ = ["register_market_data_handlers"]
