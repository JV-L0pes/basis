"""Authentication HTTP endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response, status

from basis.config import Settings
from basis.kernel.domain.errors import AuthenticationError
from basis.kernel.infrastructure.http.dependencies import SettingsDep
from basis.modules.identity.application.dto import AuthenticationResult
from basis.modules.identity.application.use_cases import (
    ChangePasswordCommand,
    LoginCommand,
    LogoutAllSessions,
    LogoutCommand,
    LogoutSession,
    RefreshSessionCommand,
    RegisterUserCommand,
    UpdateProfileCommand,
)
from basis.modules.identity.presentation.dependencies import (
    AuthenticateUserDep,
    ChangePasswordDep,
    CurrentUserDep,
    GetUserDep,
    RefreshSessionDep,
    RegisterUserDep,
    UpdateProfileDep,
    get_logout_all_sessions,
    get_logout_session,
)
from basis.modules.identity.presentation.schemas import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE_NAME = "basis_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(
    response: Response, result: AuthenticationResult, settings: Settings
) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=result.refresh.token,
        max_age=result.refresh.ttl_seconds,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path=REFRESH_COOKIE_PATH)


def _auth_response(result: AuthenticationResult) -> AuthResponse:
    return AuthResponse(
        user=UserResponse.from_view(result.user),
        token=TokenResponse(access_token=result.access.token, expires_in=result.access.ttl_seconds),
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (the first one becomes an admin)",
)
async def register(
    payload: RegisterRequest,
    use_case: RegisterUserDep,
    response: Response,
    settings: SettingsDep,
) -> AuthResponse:
    result = await use_case.execute(
        RegisterUserCommand(
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
        )
    )
    _set_refresh_cookie(response, result, settings)
    return _auth_response(result)


@router.post("/login", response_model=AuthResponse, summary="Authenticate with e-mail and password")
async def login(
    payload: LoginRequest,
    use_case: AuthenticateUserDep,
    response: Response,
    settings: SettingsDep,
) -> AuthResponse:
    result = await use_case.execute(LoginCommand(email=payload.email, password=payload.password))
    _set_refresh_cookie(response, result, settings)
    return _auth_response(result)


@router.post("/refresh", response_model=AuthResponse, summary="Rotate the refresh token")
async def refresh(
    use_case: RefreshSessionDep,
    response: Response,
    settings: SettingsDep,
    payload: RefreshRequest | None = None,
    cookie_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
) -> AuthResponse:
    token = payload.refresh_token if payload and payload.refresh_token else cookie_token
    if not token:
        raise AuthenticationError("Missing refresh token")
    result = await use_case.execute(RefreshSessionCommand(refresh_token=token))
    _set_refresh_cookie(response, result, settings)
    return _auth_response(result)


@router.post(
    "/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke the current session"
)
async def logout(
    use_case: Annotated[LogoutSession, Depends(get_logout_session)],
    response: Response,
    payload: RefreshRequest | None = None,
    cookie_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE_NAME)] = None,
) -> None:
    token = payload.refresh_token if payload and payload.refresh_token else cookie_token
    if token:
        await use_case.execute(LogoutCommand(refresh_token=token))
    _clear_refresh_cookie(response)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke every session of the current user",
)
async def logout_all(
    use_case: Annotated[LogoutAllSessions, Depends(get_logout_all_sessions)],
    user: CurrentUserDep,
    response: Response,
) -> None:
    await use_case.execute(user.id)
    _clear_refresh_cookie(response)


@router.get("/me", response_model=UserResponse, summary="Current user profile")
async def me(user: CurrentUserDep, use_case: GetUserDep) -> UserResponse:
    return UserResponse.from_view(await use_case.execute(user.id))


@router.patch("/me", response_model=UserResponse, summary="Update the current user profile")
async def update_me(
    payload: UpdateProfileRequest,
    use_case: UpdateProfileDep,
    user: CurrentUserDep,
) -> UserResponse:
    view = await use_case.execute(
        UpdateProfileCommand(user_id=user.id, display_name=payload.display_name)
    )
    return UserResponse.from_view(view)


@router.post(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change the current user password (revokes all sessions)",
)
async def change_password(
    payload: ChangePasswordRequest,
    use_case: ChangePasswordDep,
    user: CurrentUserDep,
    response: Response,
) -> None:
    await use_case.execute(
        ChangePasswordCommand(
            user_id=user.id,
            current_password=payload.current_password,
            new_password=payload.new_password,
        )
    )
    _clear_refresh_cookie(response)


__all__ = ["router"]
