"""Session issuing: access/refresh pairs and server-side refresh registration."""

from __future__ import annotations

from datetime import datetime

from basis.kernel.domain.clock import Clock
from basis.kernel.domain.identifiers import new_id
from basis.modules.identity.application.dto import AuthenticationResult, UserView
from basis.modules.identity.domain.models import User
from basis.modules.identity.domain.ports import (
    IssuedToken,
    RefreshTokenRecord,
    RefreshTokenRepository,
    TokenService,
)
from basis.modules.identity.domain.security import token_digest


class SessionIssuer:
    """Creates token pairs and records refresh sessions for rotation/revocation."""

    def __init__(
        self,
        *,
        tokens: TokenService,
        refresh_tokens: RefreshTokenRepository,
        clock: Clock,
    ) -> None:
        self._tokens = tokens
        self._refresh_tokens = refresh_tokens
        self._clock = clock

    async def issue(self, user: User) -> AuthenticationResult:
        """Issue a fresh token pair for ``user`` and persist the refresh session."""
        now = self._clock.now()
        access = self._tokens.create_access_token(user_id=user.id, role=user.role, now=now)
        refresh = self._tokens.create_refresh_token(user_id=user.id, now=now)
        await self._register_refresh(user, refresh, now)
        return AuthenticationResult(user=UserView.from_entity(user), access=access, refresh=refresh)

    async def _register_refresh(self, user: User, refresh: IssuedToken, now: datetime) -> None:
        await self._refresh_tokens.add(
            RefreshTokenRecord(
                id=new_id(),
                user_id=user.id,
                token_digest=token_digest(refresh.token),
                expires_at=refresh.expires_at,
                created_at=now,
            )
        )


__all__ = ["SessionIssuer"]
