"""Read models (DTOs) for the identity context."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from basis.modules.identity.domain.models import User
from basis.modules.identity.domain.ports import IssuedToken


@dataclass(frozen=True, slots=True)
class UserView:
    """Public representation of a user."""

    id: UUID
    email: str
    display_name: str
    role: str
    is_active: bool
    created_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> UserView:
        return cls(
            id=user.id,
            email=str(user.email),
            display_name=user.display_name,
            role=str(user.role),
            is_active=user.is_active,
            created_at=user.created_at,
        )

    @classmethod
    def from_entities(cls, users: Iterable[User]) -> list[UserView]:
        return [cls.from_entity(user) for user in users]


@dataclass(frozen=True, slots=True)
class AuthenticationResult:
    """The outcome of a successful login/registration/refresh."""

    user: UserView
    access: IssuedToken
    refresh: IssuedToken


__all__ = ["AuthenticationResult", "UserView"]
