"""The User aggregate."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from basis.kernel.domain.clock import Clock
from basis.kernel.domain.entity import AggregateRoot
from basis.kernel.domain.errors import InvariantViolationError, ValidationError
from basis.kernel.domain.identifiers import new_id
from basis.modules.identity.domain.events import (
    UserDeactivated,
    UserPasswordChanged,
    UserRegistered,
)
from basis.modules.identity.domain.value_objects import (
    DISPLAY_NAME_MAX_LENGTH,
    DISPLAY_NAME_MIN_LENGTH,
    Email,
    Role,
)


def _validate_display_name(display_name: str) -> str:
    normalized = " ".join(display_name.split())
    if not (DISPLAY_NAME_MIN_LENGTH <= len(normalized) <= DISPLAY_NAME_MAX_LENGTH):
        raise ValidationError(
            f"Name must be between {DISPLAY_NAME_MIN_LENGTH} and "
            f"{DISPLAY_NAME_MAX_LENGTH} characters",
            details={"length": len(normalized)},
        )
    return normalized


@dataclass(eq=False, slots=True)
class User(AggregateRoot[UUID]):
    """A platform user (admin, advisor or viewer)."""

    email: Email
    display_name: str
    role: Role
    password_hash: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def register(
        cls,
        *,
        email: Email,
        display_name: str,
        role: Role,
        password_hash: str,
        clock: Clock,
    ) -> User:
        """Create a new active user and record :class:`UserRegistered`."""
        moment = clock.now()
        user = cls(
            id=new_id(),
            email=email,
            display_name=_validate_display_name(display_name),
            role=role,
            password_hash=password_hash,
            is_active=True,
            created_at=moment,
            updated_at=moment,
        )
        user.record(
            UserRegistered(
                occurred_at=moment,
                user_id=user.id,
                email=str(email),
                role=str(role),
            )
        )
        return user

    def rename(self, display_name: str, *, clock: Clock) -> None:
        """Change the display name."""
        self.display_name = _validate_display_name(display_name)
        self.updated_at = clock.now()

    def change_password(self, password_hash: str, *, clock: Clock) -> None:
        """Replace the stored password hash."""
        if password_hash == self.password_hash:
            raise InvariantViolationError("New password must differ from the current one")
        moment = clock.now()
        self.password_hash = password_hash
        self.updated_at = moment
        self.record(UserPasswordChanged(occurred_at=moment, user_id=self.id))

    def grant_role(self, role: Role, *, clock: Clock) -> None:
        """Grant a new role (admin-only operation, enforced in the application layer)."""
        self.role = role
        self.updated_at = clock.now()

    def deactivate(self, *, clock: Clock) -> None:
        """Deactivate the account. Idempotent."""
        if not self.is_active:
            return
        moment = clock.now()
        self.is_active = False
        self.updated_at = moment
        self.record(UserDeactivated(occurred_at=moment, user_id=self.id))

    def activate(self, *, clock: Clock) -> None:
        """Reactivate a previously deactivated account. Idempotent."""
        if self.is_active:
            return
        self.is_active = True
        self.updated_at = clock.now()

    def can_manage_clients(self) -> bool:
        return self.is_active and self.role.can_manage_clients()


__all__ = ["User"]
