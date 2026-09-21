"""RFC 9457 problem details for every error surfaced by the API."""

from __future__ import annotations

import json
from typing import Any

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from basis.config import Settings
from basis.kernel.domain.errors import BasisError, ValidationError
from basis.logging import get_logger

logger = get_logger("http.errors")

PROBLEM_CONTENT_TYPE = "application/problem+json"
PROBLEM_TYPE_BASE = "https://basis.dev/problems"


def problem_response(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: str,
    code: str,
    errors: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    """Build an ``application/problem+json`` response per RFC 9457."""
    body: dict[str, Any] = {
        "type": f"{PROBLEM_TYPE_BASE}/{code}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": request.url.path,
        "code": code,
    }
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        body["request_id"] = str(request_id)
    if errors:
        body["errors"] = errors
    return Response(
        content=json.dumps(body, ensure_ascii=False),
        status_code=status_code,
        media_type=PROBLEM_CONTENT_TYPE,
        headers=headers,
    )


def _serialize_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    return [
        {
            "loc": [str(part) for part in error.get("loc", ())],
            "msg": str(error.get("msg", "")),
            "type": str(error.get("type", "")),
        }
        for error in exc.errors()
    ]


def register_exception_handlers(app: FastAPI, settings: Settings) -> None:
    """Attach problem-details handlers to the application."""

    async def handle_basis_error(request: Request, exc: Exception) -> Response:
        if not isinstance(exc, BasisError):  # pragma: no cover - defensive
            raise exc
        if exc.http_status >= 500:
            logger.error("application_error", code=exc.code, detail=exc.message, exc_info=exc)
        return problem_response(
            request,
            status_code=exc.http_status,
            title=exc.title,
            detail=exc.message,
            code=exc.code,
            errors=[{"detail": exc.details}] if exc.details else None,
        )

    async def handle_request_validation(request: Request, exc: Exception) -> Response:
        if not isinstance(exc, RequestValidationError):  # pragma: no cover - defensive
            raise exc
        return problem_response(
            request,
            status_code=ValidationError.http_status,
            title=ValidationError.title,
            detail="The request payload or parameters are invalid.",
            code=ValidationError.code,
            errors=_serialize_validation_errors(exc),
        )

    async def handle_http_exception(request: Request, exc: Exception) -> Response:
        if not isinstance(exc, StarletteHTTPException):  # pragma: no cover - defensive
            raise exc
        detail = exc.detail if isinstance(exc.detail, str) else "HTTP error"
        return problem_response(
            request,
            status_code=exc.status_code,
            title=detail,
            detail=detail,
            code=f"http_{exc.status_code}",
            headers=dict(exc.headers or {}),
        )

    async def handle_unexpected(request: Request, exc: Exception) -> Response:
        logger.error("unhandled_exception", error=repr(exc), exc_info=exc)
        detail = (
            repr(exc)
            if settings.debug
            else "An unexpected error occurred. Contact support with the request id."
        )
        return problem_response(
            request,
            status_code=500,
            title="Internal server error",
            detail=detail,
            code="internal_error",
        )

    app.add_exception_handler(BasisError, handle_basis_error)
    app.add_exception_handler(RequestValidationError, handle_request_validation)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(Exception, handle_unexpected)


__all__ = [
    "PROBLEM_CONTENT_TYPE",
    "problem_response",
    "register_exception_handlers",
]
