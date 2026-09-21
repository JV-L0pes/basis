"""Domain ports (protocols) for the identity context, plus token records."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from basis.modules.identity.domain.models import User
from basis.modules.identity.domain.value_objects import Email, PlainPassword, Role


@dataclass(slots=True)
class RefreshTokenRecord:
    """Server-side state of a refresh token. Only its digest is stored."""

    id: UUID
    user_id: UUID
    token_digest: str
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None = None
    replaced_by_digest: str | None = None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    def is_expired(self, now: datetime) -> bool:
        return self.expires_at <= now

    def is_usable(self, now: datetime) -> bool:
        return not self.is_revoked and not self.is_expired(now)


@dataclass(frozen=True, slots=True)
class IssuedToken:
    """A freshly signed token, its expiry instant and lifetime."""

    token: str
    expires_at: datetime
    ttl_seconds: int


@dataclass(frozen=True, slots=True)
class TokenPair:
    access: IssuedToken
    refresh: IssuedToken

    def __repr__(self) -> str:
        return f"TokenPair(access_expires_at={self.access.expires_at!r}, refresh_expires_at={self.refresh.expires_at!r})"


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Validated claims extracted from an access token."""

    subject: UUID
    role: Role
    expires_at: datetime


class UserRepository(Protocol):
    """Persistence port for the User aggregate."""

    async def get(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: Email) -> User | None: ...

    async def add(self, user: User) -> None: ...

    async def update(self, user: User) -> None: ...

    async def count(self) -> int: ...


class PasswordHasher(Protocol):
    """Salted, memory-hard password hashing."""

    def hash(self, password: PlainPassword) -> str: ...

    def verify(self, password: PlainPassword, password_hash: str) -> bool: ...

    def needs_rehash(self, password_hash: str) -> bool: ...

    def dummy_hash(self) -> str:
        """A valid hash of a random value, used to equalise login timing."""
        ...


class TokenService(Protocol):
    """Access/refresh token issuing and validation."""

    def create_access_token(self, *, user_id: UUID, role: Role, now: datetime) -> IssuedToken: ...

    def create_refresh_token(self, *, user_id: UUID, now: datetime) -> IssuedToken: ...

    def decode_access_token(self, token: str, *, now: datetime) -> AccessTokenClaims: ...


class RefreshTokenRepository(Protocol):
    """Persistence port for refresh-token sessions."""

    async def add(self, record: RefreshTokenRecord) -> None: ...

    async def get_by_digest(self, digest: str) -> RefreshTokenRecord | None: ...

    async def update(self, record: RefreshTokenRecord) -> None: ...

    async def revoke_all_for_user(self, user_id: UUID, *, at: datetime) -> int: ...

    async def list_active_for_user(
        self, user_id: UUID, *, now: datetime
    ) -> Sequence[RefreshTokenRecord]: ...


__all__ = [
    "AccessTokenClaims",
    "IssuedToken",
    "PasswordHasher",
    "RefreshTokenRecord",
    "RefreshTokenRepository",
    "TokenPair",
    "TokenService",
    "UserRepository",
]
