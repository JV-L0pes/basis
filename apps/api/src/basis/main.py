"""Application factory, lifespan and root endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from basis import __version__
from basis.api import api_v1
from basis.config import Settings, get_settings
from basis.kernel.domain.clock import SystemClock
from basis.kernel.infrastructure.db import create_engine, create_session_factory
from basis.kernel.infrastructure.events import InProcessEventBus
from basis.kernel.infrastructure.http.errors import register_exception_handlers
from basis.kernel.infrastructure.http.middleware import RequestContextMiddleware
from basis.logging import configure_logging, get_logger
from basis.modules.clients.application.event_handlers import register_clients_handlers
from basis.modules.identity.application.event_handlers import register_identity_handlers
from basis.modules.identity.domain.value_objects import PasswordPolicy
from basis.modules.identity.infrastructure.hashing import Argon2idHasher
from basis.modules.identity.infrastructure.tokens import JwtTokenService
from basis.modules.identity.presentation.dependencies import IdentityRuntime
from basis.modules.market_data.application.event_handlers import register_market_data_handlers
from basis.modules.market_data.presentation.dependencies import (
    build_market_data_runtime,
)
from basis.modules.portfolio.application.event_handlers import register_portfolio_handlers

logger = get_logger("app")

DESCRIPTION = """
**Basis** is an investment management platform for the Brazilian financial market.

The API is a modular monolith: `identity`, `clients`, `portfolio`, `market_data`
and `analytics` are bounded contexts with their own domain models, exposed as a
single versioned HTTP surface.
"""


def build_identity_runtime(settings: Settings) -> IdentityRuntime:
    """Build the process-wide identity services from settings."""
    return IdentityRuntime(
        hasher=Argon2idHasher(
            time_cost=settings.auth.argon2_time_cost,
            memory_cost_kib=settings.auth.argon2_memory_cost_kib,
            parallelism=settings.auth.argon2_parallelism,
        ),
        tokens=JwtTokenService(
            secret_key=settings.secret_key.get_secret_value(),
            algorithm=settings.auth.algorithm,
            access_ttl=timedelta(minutes=settings.auth.access_token_ttl_minutes),
            refresh_ttl=timedelta(days=settings.auth.refresh_token_ttl_days),
        ),
        policy=PasswordPolicy(),
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Wire shared infrastructure on startup and dispose it on shutdown."""
    settings: Settings = app.state.settings

    engine = create_engine(settings)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)
    app.state.clock = SystemClock()

    event_bus = InProcessEventBus()
    app.state.event_bus = event_bus
    register_identity_handlers(event_bus)
    register_clients_handlers(event_bus)
    register_market_data_handlers(event_bus)
    register_portfolio_handlers(event_bus)

    app.state.identity_runtime = build_identity_runtime(settings)
    app.state.market_data_runtime = build_market_data_runtime(settings)

    logger.info(
        "application_started",
        environment=settings.environment,
        version=__version__,
    )
    try:
        yield
    finally:
        await engine.dispose()
        logger.info("application_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application (also used directly by tests)."""
    resolved = settings or get_settings()
    configure_logging(resolved)

    app = FastAPI(
        title=resolved.app_name,
        version=__version__,
        description=DESCRIPTION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
    )
    app.state.settings = resolved

    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )

    register_exception_handlers(app, resolved)
    app.include_router(api_v1)
    return app


app = create_app()


__all__ = ["app", "build_identity_runtime", "create_app", "lifespan"]
