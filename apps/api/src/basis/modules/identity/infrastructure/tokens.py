"""Token issuing: JWT access tokens and opaque, rotating refresh tokens."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import secrets
from typing import Any
from uuid import UUID, uuid4

import jwt
from jwt.exceptions import InvalidTokenError

from basis.kernel.domain.errors import AuthenticationError
from basis.modules.identity.domain.ports import AccessTokenClaims, IssuedToken
from basis.modules.identity.domain.value_objects import Role


class JwtTokenService:
    """Access tokens are signed JWTs; refresh tokens are opaque random secrets.

    Refresh tokens never carry claims, so they can only be used against the
    server-side session registry — which is what makes rotation and reuse
    detection possible.
    """

    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str = "HS256",
        access_ttl: timedelta,
        refresh_ttl: timedelta,
        issuer: str = "basis-api",
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl
        self._issuer = issuer

    def create_access_token(self, *, user_id: UUID, role: Role, now: datetime) -> IssuedToken:
        expires_at = now + self._access_ttl
        payload: dict[str, Any] = {
            "sub": str(user_id),
            "role": str(role),
            "type": "access",
            "iss": self._issuer,
            "jti": str(uuid4()),
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        token = jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
        return IssuedToken(
            token=token, expires_at=expires_at, ttl_seconds=int(self._access_ttl.total_seconds())
        )

    def create_refresh_token(self, *, user_id: UUID, now: datetime) -> IssuedToken:
        del user_id  # the subject lives in the server-side registry
        return IssuedToken(
            token=secrets.token_urlsafe(48),
            expires_at=now + self._refresh_ttl,
            ttl_seconds=int(self._refresh_ttl.total_seconds()),
        )

    def decode_access_token(self, token: str, *, now: datetime) -> AccessTokenClaims:
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
                issuer=self._issuer,
                options={"verify_exp": False, "require": ["exp", "iat", "sub", "iss"]},
            )
        except InvalidTokenError as exc:
            raise AuthenticationError("Invalid or malformed access token") from exc

        if payload.get("type") != "access":
            raise AuthenticationError("Provided token is not an access token")

        try:
            subject = UUID(str(payload["sub"]))
            role = Role(str(payload["role"]))
            expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=UTC)
        except (KeyError, ValueError, TypeError) as exc:
            raise AuthenticationError("Access token has invalid claims") from exc

        if expires_at <= now:
            raise AuthenticationError("Access token has expired")

        return AccessTokenClaims(subject=subject, role=role, expires_at=expires_at)


__all__ = ["JwtTokenService"]
