"""Time abstraction. Domain code never calls ``datetime.now`` directly."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Port for obtaining the current time.

    Injecting a clock keeps aggregates deterministic and testable.
    """

    def now(self) -> datetime:
        """Return the current instant, timezone-aware (UTC)."""
        ...

    def today(self) -> date:
        """Return the current calendar date, timezone-aware (UTC)."""
        ...


class SystemClock:
    """Production clock backed by the operating system."""

    __slots__ = ()

    def now(self) -> datetime:
        return datetime.now(UTC)

    def today(self) -> date:
        return self.now().date()


class FrozenClock:
    """Deterministic clock for tests. Time only moves when told to."""

    __slots__ = ("_now",)

    def __init__(self, moment: datetime) -> None:
        if moment.tzinfo is None:
            raise ValueError("FrozenClock requires a timezone-aware datetime")
        self._now = moment

    def now(self) -> datetime:
        return self._now

    def today(self) -> date:
        return self._now.date()

    def advance(self, delta: timedelta) -> None:
        self._now += delta

    def set(self, moment: datetime) -> None:
        if moment.tzinfo is None:
            raise ValueError("FrozenClock requires a timezone-aware datetime")
        self._now = moment
