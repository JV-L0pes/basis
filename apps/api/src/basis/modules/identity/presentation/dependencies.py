"""Composition root for the identity context: FastAPI dependency providers."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from basis.kernel.domain.errors import AuthenticationError, PermissionDeniedError
from basis.kernel.infrastructure.http.dependencies import (
    ClockDep,
    EventBusDep,
    SessionDep,
    UnitOfWorkDep,
)
from basis.modules.identity.application.sessions import SessionIssuer
from basis.modules.identity.application.use_cases import (
    AuthenticateUser,
    ChangePassword,
    GetUser,
    LogoutAllSessions,
    LogoutSession,
    RefreshSession,
    RegisterUser,
    UpdateProfile,
)
from basis.modules.identity.domain.models import User
from basis.modules.identity.domain.ports import (
    PasswordHasher,
    RefreshTokenRepository,
    TokenService,
    UserRepository,
)
from basis.modules.identity.domain.value_objects import PasswordPolicy, Role
from basis.modules.identity.infrastructure.repository import (
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyUserRepository,
)

bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")


@dataclass(frozen=True, slots=True)
class IdentityRuntime:
    """Process-wide identity services, built once at application startup."""

    hasher: PasswordHasher
    tokens: TokenService
    policy: PasswordPolicy


# -- runtime singletons -------------------------------------------------------
def get_identity_runtime(request: Request) -> IdentityRuntime:
    runtime: IdentityRuntime = request.app.state.identity_runtime
    return runtime


RuntimeDep = Annotated[IdentityRuntime, Depends(get_identity_runtime)]


def get_password_hasher(runtime: RuntimeDep) -> PasswordHasher:
    return runtime.hasher


def get_token_service(runtime: RuntimeDep) -> TokenService:
    return runtime.tokens


def get_password_policy(runtime: RuntimeDep) -> PasswordPolicy:
    return runtime.policy


HasherDep = Annotated[PasswordHasher, Depends(get_password_hasher)]
PolicyDep = Annotated[PasswordPolicy, Depends(get_password_policy)]


# -- repositories -------------------------------------------------------------
def get_user_repository(session: SessionDep) -> UserRepository:
    return SqlAlchemyUserRepository(session)


def get_refresh_token_repository(session: SessionDep) -> RefreshTokenRepository:
    return SqlAlchemyRefreshTokenRepository(session)


UserRepoDep = Annotated[UserRepository, Depends(get_user_repository)]
RefreshRepoDep = Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)]


# -- use cases ----------------------------------------------------------------
def get_session_issuer(
    runtime: RuntimeDep,
    refresh_tokens: RefreshRepoDep,
    clock: ClockDep,
) -> SessionIssuer:
    return SessionIssuer(tokens=runtime.tokens, refresh_tokens=refresh_tokens, clock=clock)


SessionIssuerDep = Annotated[SessionIssuer, Depends(get_session_issuer)]


def get_register_user(
    users: UserRepoDep,
    hasher: HasherDep,
    policy: PolicyDep,
    sessions: SessionIssuerDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
    events: EventBusDep,
) -> RegisterUser:
    return RegisterUser(
        users=users,
        hasher=hasher,
        policy=policy,
        sessions=sessions,
        clock=clock,
        uow=uow,
        events=events,
    )


def get_authenticate_user(
    users: UserRepoDep,
    hasher: HasherDep,
    sessions: SessionIssuerDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
) -> AuthenticateUser:
    return AuthenticateUser(users=users, hasher=hasher, sessions=sessions, clock=clock, uow=uow)


def get_refresh_session(
    users: UserRepoDep,
    refresh_tokens: RefreshRepoDep,
    sessions: SessionIssuerDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
) -> RefreshSession:
    return RefreshSession(
        users=users,
        refresh_tokens=refresh_tokens,
        sessions=sessions,
        clock=clock,
        uow=uow,
    )


def get_logout_session(
    refresh_tokens: RefreshRepoDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
) -> LogoutSession:
    return LogoutSession(refresh_tokens=refresh_tokens, clock=clock, uow=uow)


def get_logout_all_sessions(
    refresh_tokens: RefreshRepoDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
) -> LogoutAllSessions:
    return LogoutAllSessions(refresh_tokens=refresh_tokens, clock=clock, uow=uow)


def get_get_user(users: UserRepoDep) -> GetUser:
    return GetUser(users=users)


def get_change_password(
    users: UserRepoDep,
    hasher: HasherDep,
    policy: PolicyDep,
    refresh_tokens: RefreshRepoDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
    events: EventBusDep,
) -> ChangePassword:
    return ChangePassword(
        users=users,
        hasher=hasher,
        policy=policy,
        refresh_tokens=refresh_tokens,
        clock=clock,
        uow=uow,
        events=events,
    )


def get_update_profile(
    users: UserRepoDep,
    clock: ClockDep,
    uow: UnitOfWorkDep,
) -> UpdateProfile:
    return UpdateProfile(users=users, clock=clock, uow=uow)


RegisterUserDep = Annotated[RegisterUser, Depends(get_register_user)]
AuthenticateUserDep = Annotated[AuthenticateUser, Depends(get_authenticate_user)]
RefreshSessionDep = Annotated[RefreshSession, Depends(get_refresh_session)]
LogoutSessionDep = Annotated[LogoutSession, Depends(get_logout_session)]
LogoutAllDep = Annotated[LogoutAllSessions, Depends(get_logout_all_sessions)]
GetUserDep = Annotated[GetUser, Depends(get_get_user)]
ChangePasswordDep = Annotated[ChangePassword, Depends(get_change_password)]
UpdateProfileDep = Annotated[UpdateProfile, Depends(get_update_profile)]


# -- authentication guards ----------------------------------------------------
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    runtime: RuntimeDep,
    clock: ClockDep,
    users: UserRepoDep,
) -> User:
    """Resolve the authenticated user from the ``Authorization: Bearer`` header."""
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Missing bearer token")

    claims = runtime.tokens.decode_access_token(credentials.credentials, now=clock.now())
    user = await users.get(claims.subject)
    if user is None or not user.is_active:
        raise AuthenticationError("Account is not available")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role) -> Callable[..., Awaitable[User]]:
    """Build a dependency that only allows the given roles."""

    async def guard(user: CurrentUserDep) -> User:
        if user.role not in roles:
            raise PermissionDeniedError(
                "You do not have permission to perform this action",
                details={"required_roles": [str(role) for role in roles]},
            )
        return user

    return guard


AdminDep = Annotated[User, Depends(require_roles(Role.ADMIN))]
ManagerDep = Annotated[User, Depends(require_roles(Role.ADMIN, Role.ADVISOR))]


__all__ = [
    "AdminDep",
    "AuthenticateUserDep",
    "ChangePasswordDep",
    "CurrentUserDep",
    "GetUserDep",
    "IdentityRuntime",
    "LogoutAllDep",
    "LogoutSessionDep",
    "ManagerDep",
    "RefreshSessionDep",
    "RegisterUserDep",
    "UpdateProfileDep",
    "get_current_user",
    "get_identity_runtime",
    "require_roles",
]
