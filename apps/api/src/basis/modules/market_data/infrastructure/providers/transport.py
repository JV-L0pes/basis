"""Shared HTTP transport and JSON coercion helpers for market-data providers.

A fresh :class:`httpx.AsyncClient` is created per request so providers never
hold connections bound to a particular event loop. Transient failures (transport
errors and 5xx responses) are retried with exponential backoff and only then
surfaced as :class:`ExternalServiceError`, which the HTTP layer maps to 502.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import cast

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from basis.kernel.domain.currency import BRL, Currency
from basis.kernel.domain.errors import ExternalServiceError, ValidationError

RETRY_ATTEMPTS = 3


class TransientProviderError(Exception):
    """Internal marker for failures that are worth retrying."""


class JsonHttpClient:
    """Fetches JSON documents from provider endpoints."""

    __slots__ = ("_timeout",)

    def __init__(self, *, timeout: float) -> None:
        self._timeout = timeout

    async def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        allow_not_found: bool = False,
    ) -> object:
        """Return the decoded JSON payload, or ``None`` for an allowed 404."""
        try:
            return await self._get_json(url, params=params, allow_not_found=allow_not_found)
        except (TransientProviderError, httpx.HTTPError) as exc:
            raise ExternalServiceError(
                "Market data provider request failed",
                details={"url": url},
            ) from exc

    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=0.25, min=0.25, max=2.0),
        retry=retry_if_exception_type((TransientProviderError, httpx.TransportError)),
        reraise=True,
    )
    async def _get_json(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None,
        allow_not_found: bool,
    ) -> object:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(url, params=params)
        if response.status_code == 404 and allow_not_found:
            return None
        if response.status_code >= 500:
            raise TransientProviderError(f"Provider answered {response.status_code}")
        if response.status_code >= 400:
            raise ExternalServiceError(
                "Market data provider rejected the request",
                details={"status": response.status_code, "url": url},
            )
        try:
            payload: object = response.json()
        except ValueError as exc:
            raise ExternalServiceError(
                "Market data provider returned invalid JSON", details={"url": url}
            ) from exc
        return payload


def json_field(value: object, key: str) -> object:
    """Read ``key`` from a JSON object, returning ``None`` for other shapes."""
    if isinstance(value, Mapping):
        return cast("Mapping[str, object]", value).get(key)
    return None


def json_list(value: object) -> list[object]:
    """Return ``value`` as a list of raw items, or an empty list."""
    if isinstance(value, list):
        return cast("list[object]", value)
    return []


def to_decimal(value: object, *, comma_separator: bool = False) -> Decimal | None:
    """Coerce a JSON scalar to :class:`Decimal`, honouring comma decimals."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    text = str(value).strip()
    if not text:
        return None
    if comma_separator and "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def to_utc_datetime(value: object, *, fallback: datetime) -> datetime:
    """Coerce an epoch-second or ISO-8601 value to an aware UTC datetime."""
    if isinstance(value, bool):
        return fallback
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str) and value.strip():
        try:
            moment = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return fallback
        return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)
    return fallback


def to_epoch_date(value: object) -> date | None:
    """Coerce epoch seconds to a UTC calendar date."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value, tz=UTC).date()


def to_currency(value: object) -> Currency:
    """Map a provider currency code to the registry, defaulting to BRL."""
    if isinstance(value, str):
        try:
            return Currency.of(value)
        except ValidationError:
            return BRL
    return BRL


__all__ = [
    "RETRY_ATTEMPTS",
    "JsonHttpClient",
    "TransientProviderError",
    "json_field",
    "json_list",
    "to_currency",
    "to_decimal",
    "to_epoch_date",
    "to_utc_datetime",
]
