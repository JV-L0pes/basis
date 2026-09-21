"""Mapping between persistence rows and domain objects (identity context)."""

from __future__ import annotations

from basis.modules.identity.domain.models import User
from basis.modules.identity.domain.ports import RefreshTokenRecord
from basis.modules.identity.domain.value_objects import Email, Role
from basis.modules.identity.infrastructure.models import RefreshTokenRow, UserRow


def user_to_domain(row: UserRow) -> User:
    return User(
        id=row.id,
        email=Email(row.email),
        display_name=row.display_name,
        role=Role(row.role),
        password_hash=row.password_hash,
        is_active=row.is_active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def user_to_row(user: User) -> UserRow:
    return UserRow(
        id=user.id,
        email=str(user.email),
        display_name=user.display_name,
        role=str(user.role),
        password_hash=user.password_hash,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def apply_user(user: User, row: UserRow) -> None:
    row.email = str(user.email)
    row.display_name = user.display_name
    row.role = str(user.role)
    row.password_hash = user.password_hash
    row.is_active = user.is_active
    row.updated_at = user.updated_at


def refresh_token_to_domain(row: RefreshTokenRow) -> RefreshTokenRecord:
    return RefreshTokenRecord(
        id=row.id,
        user_id=row.user_id,
        token_digest=row.token_digest,
        expires_at=row.expires_at,
        created_at=row.created_at,
        revoked_at=row.revoked_at,
        replaced_by_digest=row.replaced_by_digest,
    )


def apply_refresh_token(record: RefreshTokenRecord, row: RefreshTokenRow) -> None:
    row.expires_at = record.expires_at
    row.revoked_at = record.revoked_at
    row.replaced_by_digest = record.replaced_by_digest


__all__ = [
    "apply_refresh_token",
    "apply_user",
    "refresh_token_to_domain",
    "user_to_domain",
    "user_to_row",
]
