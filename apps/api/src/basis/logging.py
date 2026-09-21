"""Structured logging configuration (structlog + stdlib bridge)."""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from basis.config import Settings

_configured = False


def configure_logging(settings: Settings) -> None:
    """Configure structlog once per process."""
    global _configured  # noqa: PLW0603
    if _configured:
        return

    level = getattr(logging, settings.log_level)
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    renderer: Any = (
        structlog.dev.ConsoleRenderer(colors=True)
        if settings.is_local
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[*shared_processors, structlog.processors.format_exc_info, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(sys.stdout),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a bound structlog logger for the given component name."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
