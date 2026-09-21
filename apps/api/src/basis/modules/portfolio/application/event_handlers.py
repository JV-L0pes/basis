"""Portfolio event handlers."""

from __future__ import annotations

from basis.kernel.infrastructure.events import InProcessEventBus
from basis.logging import get_logger
from basis.modules.portfolio.domain.events import PortfolioOpened, TransactionRecorded

logger = get_logger("portfolio.events")


async def _on_portfolio_opened(event: PortfolioOpened) -> None:
    logger.info(
        "portfolio_opened",
        portfolio_id=str(event.portfolio_id),
        client_id=str(event.client_id),
    )


async def _on_transaction_recorded(event: TransactionRecorded) -> None:
    logger.debug(
        "transaction_recorded",
        portfolio_id=str(event.portfolio_id),
        kind=event.kind,
        symbol=event.symbol,
    )


def register_portfolio_handlers(bus: InProcessEventBus) -> None:
    """Subscribe portfolio handlers to the in-process bus."""
    bus.subscribe(PortfolioOpened, _on_portfolio_opened)
    bus.subscribe(TransactionRecorded, _on_transaction_recorded)


__all__ = ["register_portfolio_handlers"]
