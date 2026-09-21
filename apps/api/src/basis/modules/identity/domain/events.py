"""Identity domain events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar
from uuid import UUID

from basis.kernel.domain.events import DomainEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class UserRegistered(DomainEvent):
    name: ClassVar[str] = "identity.user_registered"
    user_id: UUID
    email: str
    role: str


@dataclass(frozen=True, slots=True, kw_only=True)
class UserPasswordChanged(DomainEvent):
    name: ClassVar[str] = "identity.user_password_changed"
    user_id: UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class UserDeactivated(DomainEvent):
    name: ClassVar[str] = "identity.user_deactivated"
    user_id: UUID


__all__ = ["UserDeactivated", "UserPasswordChanged", "UserRegistered"]
