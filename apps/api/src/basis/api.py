"""Aggregated HTTP API: every module's router mounted under ``/api/v1``."""

from __future__ import annotations

from typing import TypedDict

from fastapi import APIRouter, Request
from sqlalchemy import text

from basis import __version__
from basis.config import Settings
from basis.kernel.infrastructure.http.dependencies import ClockDep
from basis.modules.analytics.presentation.router import router as analytics_router
from basis.modules.clients.presentation.router import router as clients_router
from basis.modules.identity.presentation.router import router as identity_router
from basis.modules.market_data.presentation.router import router as market_router
from basis.modules.portfolio.presentation.router import router as portfolio_router

api_v1 = APIRouter(prefix="/api/v1")
api_v1.include_router(identity_router)
api_v1.include_router(clients_router)
api_v1.include_router(market_router)
api_v1.include_router(portfolio_router)
api_v1.include_router(analytics_router)


class HealthStatus(TypedDict):
    status: str
    version: str
    environment: str
    timestamp: str


class ReadinessStatus(HealthStatus):
    database: str


@api_v1.get("/health", tags=["meta"], summary="Liveness probe")
async def health(request: Request, clock: ClockDep) -> HealthStatus:
    settings: Settings = request.app.state.settings
    return HealthStatus(
        status="ok",
        version=__version__,
        environment=settings.environment,
        timestamp=clock.now().isoformat(),
    )


@api_v1.get("/readyz", tags=["meta"], summary="Readiness probe (checks the database)")
async def readiness(request: Request, clock: ClockDep) -> ReadinessStatus:
    settings: Settings = request.app.state.settings
    engine = request.app.state.engine
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return ReadinessStatus(
        status="ok",
        version=__version__,
        environment=settings.environment,
        timestamp=clock.now().isoformat(),
        database="ok",
    )


__all__ = ["api_v1"]
