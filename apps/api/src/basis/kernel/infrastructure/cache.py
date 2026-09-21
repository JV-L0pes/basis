"""In-process TTL cache used for quotes and other short-lived provider data."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
import time


@dataclass(slots=True)
class _Entry[V]:
    value: V
    expires_at: float


class TtlCache[K, V]:
    """A tiny time-to-live cache with an injectable clock (monotonic by default)."""

    __slots__ = ("_clock", "_entries")

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._entries: dict[K, _Entry[V]] = {}

    def get(self, key: K) -> V | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self._clock():
            del self._entries[key]
            return None
        return entry.value

    def set(self, key: K, value: V, ttl_seconds: float) -> None:
        if ttl_seconds <= 0:
            return
        self._entries[key] = _Entry(value=value, expires_at=self._clock() + ttl_seconds)

    def invalidate(self, key: K) -> None:
        self._entries.pop(key, None)

    def clear(self) -> None:
        self._entries.clear()

    def __len__(self) -> int:
        return len(self._entries)

    async def get_or_create(
        self, key: K, ttl_seconds: float, factory: Callable[[], Awaitable[V]]
    ) -> V:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = await factory()
        self.set(key, value, ttl_seconds)
        return value


__all__ = ["TtlCache"]
