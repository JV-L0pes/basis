"""Unit tests for kernel building blocks: entities, events, clock, pagination, cache."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import ClassVar
from uuid import UUID

import pytest

from basis.kernel.application.pagination import (
    CursorPage,
    decode_cursor,
    encode_cursor,
    normalize_page_size,
)
from basis.kernel.domain.clock import FrozenClock, SystemClock
from basis.kernel.domain.entity import AggregateRoot
from basis.kernel.domain.errors import ValidationError
from basis.kernel.domain.events import DomainEvent
from basis.kernel.domain.identifiers import new_id
from basis.kernel.infrastructure.cache import TtlCache

MOMENT = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True, kw_only=True)
class SomethingHappened(DomainEvent):
    name: ClassVar[str] = "something_happened"
    details: str = ""


@dataclass(eq=False, slots=True)
class Thing(AggregateRoot[UUID]):
    label: str = ""

    @classmethod
    def create(cls, label: str, moment: datetime) -> Thing:
        thing = cls(id=new_id(), label=label)
        thing.record(SomethingHappened(occurred_at=moment, details=label))
        return thing


class TestEntity:
    def test_equality_is_identity_based(self) -> None:
        thing = Thing.create("a", MOMENT)
        same = Thing(id=thing.id, label="different label")
        assert thing == same
        assert hash(thing) == hash(same)

    def test_different_ids_are_not_equal(self) -> None:
        assert Thing.create("a", MOMENT) != Thing.create("a", MOMENT)

    def test_entity_base_compares_by_class_and_id(self) -> None:
        first = Thing.create("a", MOMENT)
        assert first != "not-an-entity"


class TestAggregateEvents:
    def test_records_and_pulls_events(self) -> None:
        thing = Thing.create("alpha", MOMENT)
        assert thing.has_events
        events = thing.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], SomethingHappened)
        assert events[0].details == "alpha"
        assert not thing.has_events

    def test_events_have_unique_ids(self) -> None:
        first = SomethingHappened(occurred_at=MOMENT)
        second = SomethingHappened(occurred_at=MOMENT)
        assert first.event_id != second.event_id


class TestClock:
    def test_system_clock_returns_utc_aware_datetimes(self) -> None:
        now = SystemClock().now()
        assert now.tzinfo is not None
        assert now.utcoffset() == timedelta(0)

    def test_frozen_clock_does_not_move(self) -> None:
        clock = FrozenClock(MOMENT)
        assert clock.now() == MOMENT
        assert clock.today() == MOMENT.date()

    def test_frozen_clock_advances_explicitly(self) -> None:
        clock = FrozenClock(MOMENT)
        clock.advance(timedelta(days=1))
        assert clock.now() == MOMENT + timedelta(days=1)

    def test_frozen_clock_rejects_naive_datetimes(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            FrozenClock(datetime(2026, 1, 1))


class TestPagination:
    def test_cursor_roundtrip(self) -> None:
        cursor = encode_cursor({"created_at": "2026-01-01T00:00:00Z", "id": "abc"})
        assert decode_cursor(cursor) == {
            "created_at": "2026-01-01T00:00:00Z",
            "id": "abc",
        }

    def test_cursor_is_url_safe(self) -> None:
        cursor = encode_cursor({"id": "a/b+c="})
        assert "+" not in cursor
        assert "/" not in cursor
        assert "=" not in cursor

    @pytest.mark.parametrize("cursor", ["!!!", "bm90LWpzb24", "eyJpZCI6IDEyM30"])
    def test_malformed_cursors_are_rejected(self, cursor: str) -> None:
        with pytest.raises(ValidationError, match="cursor"):
            decode_cursor(cursor)

    def test_page_size_is_clamped(self) -> None:
        assert normalize_page_size(None) == 20
        assert normalize_page_size(5) == 5
        assert normalize_page_size(9999) == 100

    def test_page_size_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            normalize_page_size(0)

    def test_cursor_page_reports_has_more(self) -> None:
        assert CursorPage(items=[1, 2], next_cursor=None).has_more is False
        assert CursorPage(items=[1, 2], next_cursor="abc").has_more is True


class TestTtlCache:
    def _clock_factory(self) -> tuple[list[float], object]:
        now = [1000.0]

        def clock() -> float:
            return now[0]

        return now, clock

    def test_returns_none_after_expiry(self) -> None:
        now, clock = self._clock_factory()
        cache: TtlCache[str, int] = TtlCache(clock=clock)  # type: ignore[arg-type]
        cache.set("a", 1, ttl_seconds=10)
        assert cache.get("a") == 1
        now[0] += 10.1
        assert cache.get("a") is None
        assert len(cache) == 0

    def test_invalidate_and_clear(self) -> None:
        cache: TtlCache[str, int] = TtlCache()
        cache.set("a", 1, ttl_seconds=10)
        cache.set("b", 2, ttl_seconds=10)
        cache.invalidate("a")
        assert cache.get("a") is None
        cache.clear()
        assert len(cache) == 0

    def test_non_positive_ttl_is_not_stored(self) -> None:
        cache: TtlCache[str, int] = TtlCache()
        cache.set("a", 1, ttl_seconds=0)
        assert cache.get("a") is None

    async def test_get_or_create_caches_factory_result(self) -> None:
        calls: list[int] = []

        async def factory() -> int:
            calls.append(1)
            return 42

        cache: TtlCache[str, int] = TtlCache()
        assert await cache.get_or_create("key", 60, factory) == 42
        assert await cache.get_or_create("key", 60, factory) == 42
        assert len(calls) == 1
