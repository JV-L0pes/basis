"""Unit tests for the JWT access-token service and refresh-token digests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from basis.kernel.domain.clock import FrozenClock
from basis.kernel.domain.errors import AuthenticationError
from basis.modules.identity.domain.security import token_digest
from basis.modules.identity.domain.value_objects import Role
from basis.modules.identity.infrastructure.tokens import JwtTokenService

MOMENT = datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
USER_ID = uuid4()


def service(**overrides: object) -> JwtTokenService:
    defaults: dict[str, object] = {
        "secret_key": "unit-test-secret-key-0123456789abcdef",
        "algorithm": "HS256",
        "access_ttl": timedelta(minutes=15),
        "refresh_ttl": timedelta(days=14),
    }
    defaults.update(overrides)
    return JwtTokenService(**defaults)  # type: ignore[arg-type]


class TestAccessTokens:
    def test_roundtrip_preserves_subject_and_role(self) -> None:
        issued = service().create_access_token(user_id=USER_ID, role=Role.ADMIN, now=MOMENT)

        claims = service().decode_access_token(issued.token, now=MOMENT)

        assert claims.subject == USER_ID
        assert claims.role is Role.ADMIN
        assert claims.expires_at == MOMENT + timedelta(minutes=15)

    def test_expired_token_is_rejected(self) -> None:
        issued = service().create_access_token(user_id=USER_ID, role=Role.VIEWER, now=MOMENT)
        with pytest.raises(AuthenticationError, match="expired"):
            service().decode_access_token(issued.token, now=MOMENT + timedelta(minutes=16))

    def test_token_signed_with_another_secret_is_rejected(self) -> None:
        issued = service().create_access_token(user_id=USER_ID, role=Role.ADMIN, now=MOMENT)
        with pytest.raises(AuthenticationError, match="Invalid or malformed"):
            service(secret_key="another-secret-key-0123456789abcdef").decode_access_token(
                issued.token, now=MOMENT
            )

    def test_refresh_token_cannot_be_used_as_access_token(self) -> None:
        refresh = service().create_refresh_token(user_id=USER_ID, now=MOMENT)
        with pytest.raises(AuthenticationError):
            service().decode_access_token(refresh.token, now=MOMENT)

    def test_tampered_token_is_rejected(self) -> None:
        issued = service().create_access_token(user_id=USER_ID, role=Role.ADMIN, now=MOMENT)
        assert issued.token.count(".") == 2
        forged = jwt.encode(
            {"sub": str(USER_ID), "role": "admin", "type": "access", "exp": 9_999_999_999},
            "attacker-secret-key-0123456789abcdef",
            algorithm="HS256",
        )
        with pytest.raises(AuthenticationError):
            service().decode_access_token(forged, now=MOMENT)

    def test_ttl_is_reported(self) -> None:
        issued = service().create_access_token(user_id=USER_ID, role=Role.ADMIN, now=MOMENT)
        assert issued.ttl_seconds == 900

    def test_decode_uses_the_injected_clock(self) -> None:
        frozen = FrozenClock(MOMENT)
        issued = service().create_access_token(user_id=USER_ID, role=Role.ADMIN, now=frozen.now())
        frozen.advance(timedelta(minutes=14, seconds=59))
        assert service().decode_access_token(issued.token, now=frozen.now()).subject == USER_ID


class TestRefreshTokens:
    def test_refresh_tokens_are_opaque_and_high_entropy(self) -> None:
        issued = service().create_refresh_token(user_id=USER_ID, now=MOMENT)
        assert len(issued.token) >= 64
        assert "." not in issued.token  # not a JWT
        assert issued.expires_at == MOMENT + timedelta(days=14)

    def test_digest_is_deterministic_and_not_reversible(self) -> None:
        token = "refresh-token-value"
        assert token_digest(token) == token_digest(token)
        assert token not in token_digest(token)
        assert len(token_digest(token)) == 64
