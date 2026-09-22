"""Identity use cases: register, authenticate, refresh, logout, profile."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from basis.kernel.application.ports import UnitOfWork
from basis.kernel.domain.clock import Clock
from basis.kernel.domain.errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from basis.kernel.domain.events import EventPublisher
from basis.modules.identity.application.dto import AuthenticationResult, UserView
from basis.modules.identity.application.sessions import SessionIssuer
from basis.modules.identity.domain.models import User
from basis.modules.identity.domain.ports import (
    PasswordHasher,
    RefreshTokenRecord,
    RefreshTokenRepository,
    UserRepository,
)
from basis.modules.identity.domain.security import token_digest
from basis.modules.identity.domain.value_objects import (
    Email,
    PasswordPolicy,
    PlainPassword,
    Role,
)


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    password: str
    display_name: str


# A refresh token replayed this shortly after rotation is a client race (a
# double submit, two tabs, React StrictMode), not theft: refuse the token but
# keep the session family alive. Reuse beyond the window terminates everything.
ROTATION_GRACE_SECONDS = 30


@dataclass(frozen=True, slots=True)
class LoginCommand:
    email: str
    password: str


@dataclass(frozen=True, slots=True)
class RefreshSessionCommand:
    refresh_token: str


@dataclass(frozen=True, slots=True)
class LogoutCommand:
    refresh_token: str


@dataclass(frozen=True, slots=True)
class ChangePasswordCommand:
    user_id: UUID
    current_password: str
    new_password: str


@dataclass(frozen=True, slots=True)
class UpdateProfileCommand:
    user_id: UUID
    display_name: str


def _is_rotation_race(record: RefreshTokenRecord, now: datetime) -> bool:
    """Whether a revoked token was replayed inside the rotation grace window."""
    if record.revoked_at is None or record.replaced_by_digest is None:
        return False
    elapsed = (now - record.revoked_at).total_seconds()
    return 0 <= elapsed <= ROTATION_GRACE_SECONDS


class RegisterUser:
    """Register a new user. The very first user bootstraps as ADMIN."""

    def __init__(
        self,
        *,
        users: UserRepository,
        hasher: PasswordHasher,
        policy: PasswordPolicy,
        sessions: SessionIssuer,
        clock: Clock,
        uow: UnitOfWork,
        events: EventPublisher,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._policy = policy
        self._sessions = sessions
        self._clock = clock
        self._uow = uow
        self._events = events

    async def execute(self, command: RegisterUserCommand) -> AuthenticationResult:
        email = Email(command.email)
        password = PlainPassword(command.password)
        self._policy.validate(password)

        if await self._users.get_by_email(email) is not None:
            raise ConflictError("E-mail is already registered", details={"email": str(email)})

        role = Role.ADMIN if await self._users.count() == 0 else Role.ADVISOR
        user = User.register(
            email=email,
            display_name=command.display_name,
            role=role,
            password_hash=self._hasher.hash(password),
            clock=self._clock,
        )
        await self._users.add(user)

        result = await self._sessions.issue(user)
        events = user.pull_events()
        await self._uow.commit()
        await self._events.publish(events)
        return result


class AuthenticateUser:
    """Verify credentials and open a session."""

    def __init__(
        self,
        *,
        users: UserRepository,
        hasher: PasswordHasher,
        sessions: SessionIssuer,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._sessions = sessions
        self._clock = clock
        self._uow = uow

    async def execute(self, command: LoginCommand) -> AuthenticationResult:
        email = Email(command.email)
        password = PlainPassword(command.password)
        user = await self._users.get_by_email(email)

        if user is None:
            # Equalise timing with the user-found path to avoid account enumeration.
            self._hasher.verify(password, self._hasher.dummy_hash())
            raise AuthenticationError("Invalid credentials")

        if not self._hasher.verify(password, user.password_hash):
            raise AuthenticationError("Invalid credentials")
        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        if self._hasher.needs_rehash(user.password_hash):
            user.change_password(self._hasher.hash(password), clock=self._clock)
            await self._users.update(user)

        result = await self._sessions.issue(user)
        await self._uow.commit()
        return result


class RefreshSession:
    """Rotate a refresh token, detecting reuse of revoked tokens."""

    def __init__(
        self,
        *,
        users: UserRepository,
        refresh_tokens: RefreshTokenRepository,
        sessions: SessionIssuer,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._users = users
        self._refresh_tokens = refresh_tokens
        self._sessions = sessions
        self._clock = clock
        self._uow = uow

    async def execute(self, command: RefreshSessionCommand) -> AuthenticationResult:
        now = self._clock.now()
        record = await self._refresh_tokens.get_by_digest(token_digest(command.refresh_token))
        if record is None:
            raise AuthenticationError("Invalid refresh token")

        if record.is_revoked:
            if _is_rotation_race(record, now):
                raise AuthenticationError("Refresh token was already rotated")
            # Token reuse beyond the grace window: assume theft and terminate
            # every session of that user.
            await self._refresh_tokens.revoke_all_for_user(record.user_id, at=now)
            await self._uow.commit()
            raise AuthenticationError("Refresh token has already been used")

        if record.is_expired(now):
            raise AuthenticationError("Refresh token has expired")

        user = await self._users.get(record.user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Account is not available")

        result = await self._sessions.issue(user)
        record.revoked_at = now
        record.replaced_by_digest = token_digest(result.refresh.token)
        await self._refresh_tokens.update(record)
        await self._uow.commit()
        return result


class LogoutSession:
    """Revoke the current refresh session."""

    def __init__(
        self,
        *,
        refresh_tokens: RefreshTokenRepository,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._refresh_tokens = refresh_tokens
        self._clock = clock
        self._uow = uow

    async def execute(self, command: LogoutCommand) -> None:
        record = await self._refresh_tokens.get_by_digest(token_digest(command.refresh_token))
        if record is None or record.is_revoked:
            return
        record.revoked_at = self._clock.now()
        await self._refresh_tokens.update(record)
        await self._uow.commit()


class LogoutAllSessions:
    """Revoke every refresh session of a user (used when a password changes)."""

    def __init__(
        self,
        *,
        refresh_tokens: RefreshTokenRepository,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._refresh_tokens = refresh_tokens
        self._clock = clock
        self._uow = uow

    async def execute(self, user_id: UUID) -> int:
        revoked = await self._refresh_tokens.revoke_all_for_user(user_id, at=self._clock.now())
        await self._uow.commit()
        return revoked


class GetUser:
    """Load a single user by id."""

    def __init__(self, *, users: UserRepository) -> None:
        self._users = users

    async def execute(self, user_id: UUID) -> UserView:
        user = await self._users.get(user_id)
        if user is None:
            raise NotFoundError("User not found", details={"user_id": str(user_id)})
        return UserView.from_entity(user)


class ChangePassword:
    """Change the password of an authenticated user and drop every session."""

    def __init__(
        self,
        *,
        users: UserRepository,
        hasher: PasswordHasher,
        policy: PasswordPolicy,
        refresh_tokens: RefreshTokenRepository,
        clock: Clock,
        uow: UnitOfWork,
        events: EventPublisher,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._policy = policy
        self._refresh_tokens = refresh_tokens
        self._clock = clock
        self._uow = uow
        self._events = events

    async def execute(self, command: ChangePasswordCommand) -> None:
        user = await self._users.get(command.user_id)
        if user is None:
            raise NotFoundError("User not found")

        current = PlainPassword(command.current_password)
        if not self._hasher.verify(current, user.password_hash):
            raise AuthenticationError("Current password is incorrect")

        new_password = PlainPassword(command.new_password)
        self._policy.validate(new_password)
        if new_password.value == current.value:
            raise ValidationError("New password must differ from the current one")

        user.change_password(self._hasher.hash(new_password), clock=self._clock)
        await self._users.update(user)
        await self._refresh_tokens.revoke_all_for_user(user.id, at=self._clock.now())

        events = user.pull_events()
        await self._uow.commit()
        await self._events.publish(events)


class UpdateProfile:
    """Update mutable profile fields."""

    def __init__(
        self,
        *,
        users: UserRepository,
        clock: Clock,
        uow: UnitOfWork,
    ) -> None:
        self._users = users
        self._clock = clock
        self._uow = uow

    async def execute(self, command: UpdateProfileCommand) -> UserView:
        user = await self._users.get(command.user_id)
        if user is None:
            raise NotFoundError("User not found")
        user.rename(command.display_name, clock=self._clock)
        await self._users.update(user)
        await self._uow.commit()
        return UserView.from_entity(user)


__all__ = [
    "AuthenticateUser",
    "ChangePassword",
    "ChangePasswordCommand",
    "GetUser",
    "LoginCommand",
    "LogoutAllSessions",
    "LogoutCommand",
    "LogoutSession",
    "RefreshSession",
    "RefreshSessionCommand",
    "RegisterUser",
    "RegisterUserCommand",
    "UpdateProfile",
    "UpdateProfileCommand",
]
