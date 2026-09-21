"""SQLAlchemy repositories for the identity context."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from basis.kernel.domain.errors import NotFoundError
from basis.modules.identity.domain.models import User
from basis.modules.identity.domain.ports import RefreshTokenRecord
from basis.modules.identity.domain.value_objects import Email
from basis.modules.identity.infrastructure.mappers import (
    apply_refresh_token,
    apply_user,
    refresh_token_to_domain,
    user_to_domain,
    user_to_row,
)
from basis.modules.identity.infrastructure.models import RefreshTokenRow, UserRow


class SqlAlchemyUserRepository:
    """User persistence backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: UUID) -> User | None:
        row = await self._session.get(UserRow, user_id)
        return user_to_domain(row) if row is not None else None

    async def get_by_email(self, email: Email) -> User | None:
        result = await self._session.execute(select(UserRow).where(UserRow.email == email.value))
        row = result.scalar_one_or_none()
        return user_to_domain(row) if row is not None else None

    async def add(self, user: User) -> None:
        self._session.add(user_to_row(user))
        await self._session.flush()

    async def update(self, user: User) -> None:
        row = await self._session.get(UserRow, user.id)
        if row is None:
            raise NotFoundError("User not found", details={"user_id": str(user.id)})
        apply_user(user, row)
        await self._session.flush()

    async def count(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(UserRow))
        return int(result.scalar_one())


class SqlAlchemyRefreshTokenRepository:
    """Refresh-session persistence backed by SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: RefreshTokenRecord) -> None:
        self._session.add(
            RefreshTokenRow(
                id=record.id,
                user_id=record.user_id,
                token_digest=record.token_digest,
                expires_at=record.expires_at,
                revoked_at=record.revoked_at,
                replaced_by_digest=record.replaced_by_digest,
            )
        )
        await self._session.flush()

    async def get_by_digest(self, digest: str) -> RefreshTokenRecord | None:
        result = await self._session.execute(
            select(RefreshTokenRow).where(RefreshTokenRow.token_digest == digest)
        )
        row = result.scalar_one_or_none()
        return refresh_token_to_domain(row) if row is not None else None

    async def update(self, record: RefreshTokenRecord) -> None:
        row = await self._session.get(RefreshTokenRow, record.id)
        if row is None:
            raise NotFoundError("Refresh token not found")
        apply_refresh_token(record, row)
        await self._session.flush()

    async def revoke_all_for_user(self, user_id: UUID, *, at: datetime) -> int:
        result = await self._session.execute(
            update(RefreshTokenRow)
            .where(
                RefreshTokenRow.user_id == user_id,
                RefreshTokenRow.revoked_at.is_(None),
            )
            .values(revoked_at=at)
        )
        await self._session.flush()
        return int(cast("CursorResult[Any]", result).rowcount or 0)

    async def list_active_for_user(
        self, user_id: UUID, *, now: datetime
    ) -> list[RefreshTokenRecord]:
        result = await self._session.execute(
            select(RefreshTokenRow)
            .where(
                RefreshTokenRow.user_id == user_id,
                RefreshTokenRow.revoked_at.is_(None),
                RefreshTokenRow.expires_at > now,
            )
            .order_by(RefreshTokenRow.created_at.desc())
        )
        return [refresh_token_to_domain(row) for row in result.scalars().all()]


__all__ = ["SqlAlchemyRefreshTokenRepository", "SqlAlchemyUserRepository"]
