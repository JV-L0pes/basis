"""Shared pytest fixtures: settings, schema management and database sessions."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
import sys
import warnings

from pydantic import SecretStr
import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from basis.config import AuthSettings, Settings, get_settings
from basis.kernel.infrastructure.db import Base

if sys.platform == "win32":  # psycopg's async mode needs a selector loop
    _SelectorPolicy = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    # Set it globally so anyio's blocking portals (used by TestClient) also
    # pick it up. Suppress the 3.14 deprecation of the policy API.
    if _SelectorPolicy is not None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            asyncio.set_event_loop_policy(_SelectorPolicy())
else:  # pragma: no cover - non-Windows platforms use the default policy
    _SelectorPolicy = None


@pytest.fixture(scope="session")
def event_loop_policy() -> object:
    """pytest-asyncio hook: force a selector-based loop on Windows."""
    if _SelectorPolicy is not None:
        return _SelectorPolicy()
    return asyncio.get_event_loop_policy()


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Settings pointing at the dedicated test database with fast hashing."""
    base = get_settings()
    url = base.test_database_url or base.database_url
    return Settings(
        environment="test",
        database_url=url,
        test_database_url=url,
        secret_key=SecretStr("test-secret-key-not-used-outside-tests"),
        cors_origins=["http://localhost:5173"],
        auth=AuthSettings(
            argon2_time_cost=1,
            argon2_memory_cost_kib=8,
            argon2_parallelism=1,
            access_token_ttl_minutes=15,
            refresh_token_ttl_days=14,
        ),
    )


@pytest.fixture(scope="session")
def db_url(test_settings: Settings) -> str:
    return test_settings.database_url


def truncate_all(url: str) -> None:
    """Remove every row from the public schema (test isolation helper)."""
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.begin() as connection:
            tables = (
                connection.execute(
                    text(
                        "SELECT tablename FROM pg_tables "
                        "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
                    )
                )
                .scalars()
                .all()
            )
            if tables:
                quoted = ", ".join(f'"{table}"' for table in tables)
                connection.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def schema(db_url: str) -> None:
    """Create the schema from the SQLAlchemy metadata (sync engine, no loops)."""
    engine: Engine = create_engine(db_url, poolclass=NullPool)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    engine.dispose()
    truncate_all(db_url)


@pytest.fixture(scope="session")
async def db_engine(db_url: str, schema: None) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(db_url, poolclass=NullPool)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """Session wrapped in a transaction that is always rolled back.

    SQLAlchemy's ``conditional_savepoint`` join mode means ``session.commit()``
    inside a use case only releases a savepoint, so tests stay isolated. The
    teardown is defensive: tests that deliberately trigger database errors leave
    the session in a failed state, which must not mask the test result.
    """
    connection = await db_engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)
    try:
        yield session
    finally:
        with suppress(Exception):
            await session.rollback()
        with suppress(Exception):
            await session.close()
        with suppress(Exception):
            if transaction.is_active:
                await transaction.rollback()
        with suppress(Exception):
            await connection.close()
