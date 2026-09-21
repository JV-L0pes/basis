"""HTTP client shared by the market data providers (retry, timeout, error mapping)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from basis.kernel.domain.errors import ExternalServiceError

RETRYABLE = (httpx.TransportError, httpx.HTTPStatusError)
MAX_ATTEMPTS = 3


async def fetch_json(
    url: str,
    *,
    timeout: float,
    params: Mapping[str, str] | None = None,
    headers: Mapping[str, str] | None = None,
) -> object | None:
    """GET a JSON document with retries. Returns ``None`` for 404 responses.

    Raises :class:`ExternalServiceError` when the provider keeps failing, so a
    flaky upstream never turns into a 500 on our side.
    """

    async def attempt_once() -> object | None:
        async with httpx.AsyncClient(timeout=timeout, headers=dict(headers or {})) as client:
            response = await client.get(url, params=dict(params or {}))
            if response.status_code == 404:
                return None
            if response.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"upstream error {response.status_code}",
                    request=response.request,
                    response=response,
                )
            response.raise_for_status()
            return cast("object", response.json())

    try:
        async for retry in AsyncRetrying(
            stop=stop_after_attempt(MAX_ATTEMPTS),
            wait=wait_exponential(multiplier=0.3, min=0.3, max=2),
            retry=retry_if_exception_type(RETRYABLE),
            reraise=True,
        ):
            with retry:
                return await attempt_once()
    except (httpx.HTTPError, ValueError) as exc:
        raise ExternalServiceError(
            "Market data provider is unavailable",
            details={"url": url, "reason": type(exc).__name__},
        ) from exc
    return None  # pragma: no cover - unreachable, keeps type checkers happy


__all__ = ["fetch_json"]
