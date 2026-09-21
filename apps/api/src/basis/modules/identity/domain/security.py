"""Token helpers that belong to the domain: digests are pure cryptography."""

from __future__ import annotations

import hashlib


def token_digest(token: str) -> str:
    """Return the SHA-256 hex digest used to store refresh tokens.

    Refresh tokens are high-entropy random values, so a fast digest (rather
    than a slow password hash) is the appropriate protection: it prevents the
    raw token from ever being persisted or logged.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


__all__ = ["token_digest"]
