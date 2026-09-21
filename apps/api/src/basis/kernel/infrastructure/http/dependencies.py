"""Reusable FastAPI dependencies wired to application state (composition root)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from basis.config import Settings
from basis.kernel.application.ports import UnitOfWork
from basis.kernel.domain.clock import Clock
from basis.kernel.infrastructure.db import SqlAlchemyUnitOfWork, session_scope
from basis.kernel.infrastructure.events import InProcessEventBus


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_engine(request: Request) -> AsyncEngine:
    engine: AsyncEngine = request.app.state.engine
    return engine


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    return factory


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Request-scoped session: commits on success, rolls back on error."""
    factory = get_session_factory(request)
    async for session in session_scope(factory):
        yield session


def get_clock(request: Request) -> Clock:
    clock: Clock = request.app.state.clock
    return clock


def get_event_bus(request: Request) -> InProcessEventBus:
    bus: InProcessEventBus = request.app.state.event_bus
    return bus


def get_unit_of_work(session: SessionDep) -> UnitOfWork:
    return SqlAlchemyUnitOfWork(session)


SessionDep = Annotated[AsyncSession, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]
EventBusDep = Annotated[InProcessEventBus, Depends(get_event_bus)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]

__all__ = [
    "ClockDep",
    "EventBusDep",
    "SessionDep",
    "SettingsDep",
    "UnitOfWorkDep",
    "get_clock",
    "get_engine",
    "get_event_bus",
    "get_session",
    "get_session_factory",
    "get_settings_dep",
    "get_unit_of_work",
]
