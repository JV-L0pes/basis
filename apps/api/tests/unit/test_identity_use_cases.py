"""Unit tests for identity use cases using in-memory doubles."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from basis.kernel.domain.clock import FrozenClock
from basis.kernel.domain.errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from basis.modules.identity.application.sessions import SessionIssuer
from basis.modules.identity.application.use_cases import (
    AuthenticateUser,
    ChangePassword,
    ChangePasswordCommand,
    GetUser,
    LoginCommand,
    LogoutCommand,
    LogoutSession,
    RefreshSession,
    RefreshSessionCommand,
    RegisterUser,
    RegisterUserCommand,
)
from basis.modules.identity.domain.ports import TokenPair
from basis.modules.identity.domain.security import token_digest
from basis.modules.identity.domain.value_objects import Email, PasswordPolicy, PlainPassword, Role
from tests.fakes import (
    FastHasher,
    FixedTokenService,
    InMemoryRefreshTokenRepository,
    InMemoryUserRepository,
    NoopUnitOfWork,
    NullEventPublisher,
)

MOMENT = datetime(2026, 3, 10, 9, 30, tzinfo=UTC)

GOOD_PASSWORD = "s3nh4-forte"


class Harness:
    """Wires the identity use cases against in-memory doubles."""

    def __init__(self) -> None:
        self.clock = FrozenClock(MOMENT)
        self.users = InMemoryUserRepository()
        self.refresh_tokens = InMemoryRefreshTokenRepository()
        self.hasher = FastHasher()
        self.tokens = FixedTokenService()
        self.events = NullEventPublisher()
        self.uow = NoopUnitOfWork()
        self.sessions = SessionIssuer(
            tokens=self.tokens, refresh_tokens=self.refresh_tokens, clock=self.clock
        )
        self.register = RegisterUser(
            users=self.users,
            hasher=self.hasher,
            policy=PasswordPolicy(),
            sessions=self.sessions,
            clock=self.clock,
            uow=self.uow,
            events=self.events,
        )
        self.authenticate = AuthenticateUser(
            users=self.users,
            hasher=self.hasher,
            sessions=self.sessions,
            clock=self.clock,
            uow=self.uow,
        )
        self.refresh = RefreshSession(
            users=self.users,
            refresh_tokens=self.refresh_tokens,
            sessions=self.sessions,
            clock=self.clock,
            uow=self.uow,
        )
        self.logout = LogoutSession(
            refresh_tokens=self.refresh_tokens, clock=self.clock, uow=self.uow
        )
        self.change_password = ChangePassword(
            users=self.users,
            hasher=self.hasher,
            policy=PasswordPolicy(),
            refresh_tokens=self.refresh_tokens,
            clock=self.clock,
            uow=self.uow,
            events=self.events,
        )
        self.get_user = GetUser(users=self.users)


def _register_command(
    email: str = "ana@basis.dev", password: str = GOOD_PASSWORD
) -> RegisterUserCommand:
    return RegisterUserCommand(email=email, password=password, display_name="Ana Souza")


class TestRegisterUser:
    async def test_first_user_becomes_admin(self) -> None:
        harness = Harness()
        result = await harness.register.execute(_register_command())
        assert result.user.role == Role.ADMIN
        assert result.access.token
        assert result.refresh.token
        assert harness.uow.commits == 1

    async def test_second_user_becomes_advisor(self) -> None:
        harness = Harness()
        await harness.register.execute(_register_command("ana@basis.dev"))
        result = await harness.register.execute(_register_command("bruno@basis.dev"))
        assert result.user.role == Role.ADVISOR

    async def test_duplicate_email_is_rejected(self) -> None:
        harness = Harness()
        await harness.register.execute(_register_command())
        with pytest.raises(ConflictError, match="already registered"):
            await harness.register.execute(_register_command())

    async def test_email_is_normalized_before_uniqueness_check(self) -> None:
        harness = Harness()
        await harness.register.execute(_register_command("ana@basis.dev"))
        with pytest.raises(ConflictError):
            await harness.register.execute(_register_command("  ANA@BASIS.DEV "))

    async def test_weak_password_is_rejected(self) -> None:
        harness = Harness()
        with pytest.raises(ValidationError, match="security policy"):
            await harness.register.execute(_register_command(password="fraca"))

    async def test_registration_records_refresh_session_and_event(self) -> None:
        harness = Harness()
        result = await harness.register.execute(_register_command())
        digest = token_digest(result.refresh.token)
        assert harness.refresh_tokens.records[digest].user_id == result.user.id
        assert len(harness.events.published) == 1


class TestAuthenticateUser:
    async def test_valid_credentials_return_token_pair(self) -> None:
        harness = Harness()
        await harness.register.execute(_register_command())
        result = await harness.authenticate.execute(
            LoginCommand(email="ANA@basis.dev", password=GOOD_PASSWORD)
        )
        assert result.user.email == "ana@basis.dev"
        assert result.access.expires_at > MOMENT

    async def test_wrong_password_is_rejected(self) -> None:
        harness = Harness()
        await harness.register.execute(_register_command())
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            await harness.authenticate.execute(
                LoginCommand(email="ana@basis.dev", password="outra-senha-1")
            )

    async def test_unknown_email_is_rejected_without_leaking_existence(self) -> None:
        harness = Harness()
        with pytest.raises(AuthenticationError, match="Invalid credentials"):
            await harness.authenticate.execute(
                LoginCommand(email="ghost@basis.dev", password=GOOD_PASSWORD)
            )

    async def test_inactive_account_cannot_login(self) -> None:
        harness = Harness()
        await harness.register.execute(_register_command())
        user = await harness.users.get_by_email(_to_email("ana@basis.dev"))
        assert user is not None
        user.deactivate(clock=harness.clock)
        await harness.users.update(user)
        with pytest.raises(AuthenticationError, match="deactivated"):
            await harness.authenticate.execute(
                LoginCommand(email="ana@basis.dev", password=GOOD_PASSWORD)
            )


def _to_email(value: str) -> Email:
    return Email(value)


class TestRefreshSession:
    async def test_rotates_refresh_token_and_revokes_previous(self) -> None:
        harness = Harness()
        registered = await harness.register.execute(_register_command())
        old_digest = token_digest(registered.refresh.token)

        rotated = await harness.refresh.execute(
            RefreshSessionCommand(refresh_token=registered.refresh.token)
        )

        assert rotated.refresh.token != registered.refresh.token
        old_record = harness.refresh_tokens.records[old_digest]
        assert old_record.revoked_at == MOMENT
        assert old_record.replaced_by_digest == token_digest(rotated.refresh.token)

    async def test_reuse_of_revoked_token_revokes_every_session(self) -> None:
        harness = Harness()
        registered = await harness.register.execute(_register_command())
        rotated = await harness.refresh.execute(
            RefreshSessionCommand(refresh_token=registered.refresh.token)
        )

        with pytest.raises(AuthenticationError, match="already been used"):
            await harness.refresh.execute(
                RefreshSessionCommand(refresh_token=registered.refresh.token)
            )

        for record in harness.refresh_tokens.records.values():
            assert record.revoked_at is not None
        # The rotated session was terminated as well (theft response).
        assert (
            harness.refresh_tokens.records[token_digest(rotated.refresh.token)].revoked_at
            is not None
        )

    async def test_expired_refresh_token_is_rejected(self) -> None:
        harness = Harness()
        registered = await harness.register.execute(_register_command())
        harness.clock.advance(timedelta(days=15))
        with pytest.raises(AuthenticationError, match="expired"):
            await harness.refresh.execute(
                RefreshSessionCommand(refresh_token=registered.refresh.token)
            )

    async def test_unknown_refresh_token_is_rejected(self) -> None:
        harness = Harness()
        with pytest.raises(AuthenticationError, match="Invalid refresh token"):
            await harness.refresh.execute(RefreshSessionCommand(refresh_token="nao-existe"))


class TestLogoutSession:
    async def test_logout_revokes_only_the_given_session(self) -> None:
        harness = Harness()
        first = await harness.register.execute(_register_command())
        second = await harness.refresh.execute(
            RefreshSessionCommand(refresh_token=first.refresh.token)
        )

        await harness.logout.execute(LogoutCommand(refresh_token=second.refresh.token))

        assert (
            harness.refresh_tokens.records[token_digest(second.refresh.token)].revoked_at
            is not None
        )
        assert (
            harness.refresh_tokens.records[token_digest(first.refresh.token)].revoked_at is not None
        )

    async def test_logout_with_unknown_token_is_a_noop(self) -> None:
        harness = Harness()
        await harness.logout.execute(LogoutCommand(refresh_token="nao-existe"))


class TestChangePassword:
    async def test_changes_hash_and_revokes_sessions(self) -> None:
        harness = Harness()
        registered = await harness.register.execute(_register_command())

        await harness.change_password.execute(
            ChangePasswordCommand(
                user_id=registered.user.id,
                current_password=GOOD_PASSWORD,
                new_password="nova-s3nh4-2026",
            )
        )

        user = await harness.users.get(registered.user.id)
        assert user is not None
        assert harness.hasher.verify(_plain("nova-s3nh4-2026"), user.password_hash)
        assert (
            harness.refresh_tokens.records[token_digest(registered.refresh.token)].revoked_at
            is not None
        )

    async def test_wrong_current_password_is_rejected(self) -> None:
        harness = Harness()
        registered = await harness.register.execute(_register_command())
        with pytest.raises(AuthenticationError, match="Current password"):
            await harness.change_password.execute(
                ChangePasswordCommand(
                    user_id=registered.user.id,
                    current_password="senha-errada-1",
                    new_password="nova-s3nh4-2026",
                )
            )

    async def test_new_password_must_satisfy_policy(self) -> None:
        harness = Harness()
        registered = await harness.register.execute(_register_command())
        with pytest.raises(ValidationError, match="security policy"):
            await harness.change_password.execute(
                ChangePasswordCommand(
                    user_id=registered.user.id,
                    current_password=GOOD_PASSWORD,
                    new_password="fraca",
                )
            )

    async def test_reusing_current_password_is_rejected(self) -> None:
        harness = Harness()
        registered = await harness.register.execute(_register_command())
        with pytest.raises(ValidationError, match="must differ"):
            await harness.change_password.execute(
                ChangePasswordCommand(
                    user_id=registered.user.id,
                    current_password=GOOD_PASSWORD,
                    new_password=GOOD_PASSWORD,
                )
            )


class TestGetUser:
    async def test_returns_view(self) -> None:
        harness = Harness()
        registered = await harness.register.execute(_register_command())
        view = await harness.get_user.execute(registered.user.id)
        assert view.email == "ana@basis.dev"

    async def test_unknown_user_raises(self) -> None:
        harness = Harness()
        from uuid import uuid4

        with pytest.raises(NotFoundError):
            await harness.get_user.execute(uuid4())


def _plain(value: str) -> PlainPassword:
    return PlainPassword(value)


__all__ = ["TokenPair"]
