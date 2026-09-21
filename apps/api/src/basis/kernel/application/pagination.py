"""Cursor-based pagination shared by every list endpoint.

Cursors are opaque, URL-safe, base64-encoded JSON payloads containing the sort
key of the last item of the previous page (keyset pagination). They survive
inserts and deletes, unlike ``OFFSET``.
"""

from __future__ import annotations

import base64
import binascii
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json

from basis.kernel.domain.errors import ValidationError

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class CursorPage[T]:
    """A page of results plus an opaque cursor for the next page."""

    items: Sequence[T]
    next_cursor: str | None = None

    @property
    def has_more(self) -> bool:
        return self.next_cursor is not None


def normalize_page_size(limit: int | None, default: int = DEFAULT_PAGE_SIZE) -> int:
    """Clamp a requested page size to the allowed range."""
    if limit is None:
        return default
    if limit < 1:
        raise ValidationError("Page size must be at least 1", details={"limit": limit})
    return min(limit, MAX_PAGE_SIZE)


def encode_cursor(values: Mapping[str, str]) -> str:
    """Encode cursor values into an opaque URL-safe string."""
    payload = json.dumps(dict(values), separators=(",", ":"), sort_keys=True)
    return base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> dict[str, str]:
    """Decode an opaque cursor, raising :class:`ValidationError` when malformed."""
    padded = cursor + "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
        payload = json.loads(raw)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValidationError("Malformed pagination cursor") from exc
    if not isinstance(payload, dict) or not all(
        isinstance(value, str) for value in payload.values()
    ):
        raise ValidationError("Malformed pagination cursor")
    return {str(key): str(value) for key, value in payload.items()}


__all__ = [
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
    "CursorPage",
    "decode_cursor",
    "encode_cursor",
    "normalize_page_size",
]
