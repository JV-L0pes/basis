"""HTTP schemas for the identity context."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from basis.modules.identity.application.dto import UserView


class RegisterRequest(BaseModel):
    """Payload for self-registration. The first user becomes an admin."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "ana@basis.dev",
                "password": "s3nh4-forte",
                "display_name": "Ana Souza",
            }
        }
    )

    email: str = Field(min_length=3, max_length=254, description="E-mail address")
    password: str = Field(
        min_length=10, max_length=128, description="At least 10 characters with letters and digits"
    )
    display_name: str = Field(min_length=2, max_length=120, description="Full name")


class LoginRequest(BaseModel):
    """Payload for password authentication."""

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    """Optional body for clients that cannot use cookies."""

    refresh_token: str | None = None


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(min_length=2, max_length=120)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class UserResponse(BaseModel):
    """Public user representation."""

    id: UUID
    email: str
    display_name: str
    role: Literal["admin", "advisor", "viewer"]
    is_active: bool
    created_at: datetime

    @classmethod
    def from_view(cls, view: UserView) -> UserResponse:
        return cls(
            id=view.id,
            email=view.email,
            display_name=view.display_name,
            role=view.role,  # type: ignore[arg-type]
            is_active=view.is_active,
            created_at=view.created_at,
        )


class TokenResponse(BaseModel):
    """Access token and metadata. The refresh token travels in an httpOnly cookie."""

    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 — not a credential
    expires_in: int = Field(description="Access token lifetime in seconds")


class AuthResponse(BaseModel):
    """Authentication result returned by register/login/refresh."""

    user: UserResponse
    token: TokenResponse


__all__ = [
    "AuthResponse",
    "ChangePasswordRequest",
    "LoginRequest",
    "RefreshRequest",
    "RegisterRequest",
    "TokenResponse",
    "UpdateProfileRequest",
    "UserResponse",
]
