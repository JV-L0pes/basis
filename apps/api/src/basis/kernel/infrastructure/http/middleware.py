"""Request context middleware: correlation id, structured access logs, timings."""

from __future__ import annotations

import time
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send
import structlog

from basis.logging import get_logger

logger = get_logger("http.access")

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware:
    """Pure ASGI middleware — no BaseHTTPMiddleware overhead or streaming caveats."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = headers.get(REQUEST_ID_HEADER) or str(uuid4())
        scope.setdefault("state", {})["request_id"] = request_id

        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=scope.get("method"),
            path=scope.get("path"),
        )
        started = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                response_headers = MutableHeaders(scope=message)
                response_headers[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.info(
                "request_finished",
                status_code=status_code,
                duration_ms=duration_ms,
                client=scope.get("client", ("unknown", 0))[0],
            )
            structlog.contextvars.unbind_contextvars("request_id", "method", "path")


__all__ = ["REQUEST_ID_HEADER", "RequestContextMiddleware"]
