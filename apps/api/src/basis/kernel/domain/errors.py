"""Domain and application error hierarchy.

Every error carries a stable machine-readable ``code``. The HTTP layer maps
errors to RFC 9457 problem details documents (see
``basis.kernel.infrastructure.http.errors``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, ClassVar


class BasisError(Exception):
    """Base class for every intentional error raised by the application."""

    code: ClassVar[str] = "internal_error"
    http_status: ClassVar[int] = 500
    title: ClassVar[str] = "Internal error"

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = dict(details) if details else {}


class ValidationError(BasisError):
    """Input violates a domain rule or fails schema validation."""

    code = "validation_error"
    http_status = 422
    title = "Validation error"


class NotFoundError(BasisError):
    """A referenced resource does not exist."""

    code = "not_found"
    http_status = 404
    title = "Resource not found"


class ConflictError(BasisError):
    """The operation conflicts with the current state (uniqueness, concurrency)."""

    code = "conflict"
    http_status = 409
    title = "Conflict"


class AuthenticationError(BasisError):
    """Credentials are missing, invalid or expired."""

    code = "unauthenticated"
    http_status = 401
    title = "Authentication required"


class PermissionDeniedError(BasisError):
    """The authenticated principal is not allowed to perform the operation."""

    code = "forbidden"
    http_status = 403
    title = "Permission denied"


class InvariantViolationError(BasisError):
    """An invariant of an aggregate was violated (e.g. selling more than held)."""

    code = "invariant_violation"
    http_status = 422
    title = "Business rule violation"


class ExternalServiceError(BasisError):
    """An upstream provider failed after retries."""

    code = "upstream_error"
    http_status = 502
    title = "Upstream service error"


class RateLimitedError(BasisError):
    """The caller exceeded an allowed usage rate."""

    code = "rate_limited"
    http_status = 429
    title = "Too many requests"


def is_client_error(error: BasisError) -> bool:
    """Return ``True`` when the error is the caller's fault (4xx range)."""
    return 400 <= error.http_status < 500
