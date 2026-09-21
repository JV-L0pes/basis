"""Integration tests: identity repositories against a real PostgreSQL."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from basis.kernel.domain.clock import FrozenClock
from basis.kernel.domain.errors import NotFoundError
from basis.modules.identity.domain.models import User
from basis.modules.identity.domain.ports import RefreshTokenRecord
from basis.modules.identity.domain.value_objects import Email, Role
from basis.modules.identity.infrastructure.repository import (
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyUserRepository,
)

pytestmark = pytest.mark.integration

MOMENT = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)


def make_user(email: str = "ana@basis.dev", role: Role = Role.ADVISOR) -> User:
    return User.register(
        email=Email(email),
        display_name="Ana Souza",
        role=role,
        password_hash="hash",
        clock=FrozenClock(MOMENT),
    )


class TestUserRepository:
    async def test_add_and_get_roundtrip(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyUserRepository(db_session)
        user = make_user()
        await repository.add(user)
        await db_session.flush()

        loaded = await repository.get(user.id)
        assert loaded is not None
        assert loaded.email == user.email
        assert loaded.role is Role.ADVISOR
        assert loaded.is_active is True
        assert loaded.created_at == user.created_at

    async def test_get_returns_none_for_unknown_id(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyUserRepository(db_session)
        assert await repository.get(uuid4()) is None

    async def test_get_by_email_is_normalized(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyUserRepository(db_session)
        await repository.add(make_user("ana@basis.dev"))
        found = await repository.get_by_email(Email("  ANA@BASIS.dev "))
        assert found is not None
        assert found.email.value == "ana@basis.dev"

    async def test_update_persists_changes(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyUserRepository(db_session)
        user = make_user()
        await repository.add(user)

        clock = FrozenClock(MOMENT + timedelta(days=1))
        user.rename("Ana Maria Souza", clock=clock)
        user.deactivate(clock=clock)
        await repository.update(user)

        loaded = await repository.get(user.id)
        assert loaded is not None
        assert loaded.display_name == "Ana Maria Souza"
        assert loaded.is_active is False

    async def test_update_missing_user_raises(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyUserRepository(db_session)
        with pytest.raises(NotFoundError):
            await repository.update(make_user())

    async def test_count(self, db_session: AsyncSession) -> None:
        repository = SqlAlchemyUserRepository(db_session)
        assert await repository.count() == 0
        await repository.add(make_user("a@basis.dev"))
        await repository.add(make_user("b@basis.dev"))
        assert await repository.count() == 2


class TestRefreshTokenRepository:
    def _record(self, user_id: object, digest: str = "digest-1") -> RefreshTokenRecord:
        from uuid import UUID

        assert isinstance(user_id, UUID)
        return RefreshTokenRecord(
            id=uuid4(),
            user_id=user_id,
            token_digest=digest,
            expires_at=MOMENT + timedelta(days=14),
            created_at=MOMENT,
        )

    async def test_add_and_lookup_by_digest(self, db_session: AsyncSession) -> None:
        users = SqlAlchemyUserRepository(db_session)
        user = make_user()
        await users.add(user)
        repository = SqlAlchemyRefreshTokenRepository(db_session)
        record = self._record(user.id, "digest-abc")
        await repository.add(record)

        loaded = await repository.get_by_digest("digest-abc")
        assert loaded is not None
        assert loaded.user_id == user.id
        assert loaded.is_usable(MOMENT)

    async def test_revoke_all_for_user_marks_only_active_records(
        self, db_session: AsyncSession
    ) -> None:
        users = SqlAlchemyUserRepository(db_session)
        user = make_user()
        await users.add(user)
        repository = SqlAlchemyRefreshTokenRepository(db_session)
        await repository.add(self._record(user.id, "digest-1"))
        await repository.add(self._record(user.id, "digest-2"))
        already_revoked = self._record(user.id, "digest-3")
        already_revoked.revoked_at = MOMENT
        await repository.add(already_revoked)

        revoked = await repository.revoke_all_for_user(user.id, at=MOMENT + timedelta(hours=1))

        assert revoked == 2
        other_user = make_user("bruno@basis.dev")
        await users.add(other_user)
        assert await repository.list_active_for_user(other_user.id, now=MOMENT) == []

    async def test_delete_user_cascades_refresh_tokens(self, db_session: AsyncSession) -> None:
        from sqlalchemy import delete

        from basis.modules.identity.infrastructure.models import UserRow

        users = SqlAlchemyUserRepository(db_session)
        user = make_user()
        await users.add(user)
        repository = SqlAlchemyRefreshTokenRepository(db_session)
        await repository.add(self._record(user.id, "digest-cascade"))

        await db_session.execute(delete(UserRow).where(UserRow.id == user.id))
        await db_session.flush()

        assert await repository.get_by_digest("digest-cascade") is None
