"""Identifier generation. UUIDv7 is time-ordered, which keeps database indexes dense."""

from __future__ import annotations

import os
import sys
import time
from uuid import UUID, uuid4

if sys.version_info >= (3, 14):
    from uuid import uuid7

    def new_id() -> UUID:
        """Return a new time-ordered UUID (RFC 9562, version 7)."""
        return uuid7()

else:  # Python 3.13 compatibility layer

    def new_id() -> UUID:
        """Return a new time-ordered UUID (RFC 9562, version 7)."""
        random_bits = int.from_bytes(os.urandom(10), "big")
        timestamp_ms = time.time_ns() // 1_000_000
        value = (timestamp_ms & ((1 << 48) - 1)) << 80
        value |= 0x7 << 76
        value |= (random_bits >> 62 & 0xFFF) << 64
        value |= 0x2 << 62
        value |= random_bits & ((1 << 62) - 1)
        return UUID(int=value)


def new_correlation_id() -> UUID:
    """Return a random identifier for correlating logs across systems."""
    return uuid4()


__all__ = ["new_correlation_id", "new_id"]
