"""Unit tests for identity domain rules (no I/O, no framework)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from basis.kernel.domain.clock import FrozenClock
from basis.kernel.domain.errors import InvariantViolationError, ValidationError
from basis.modules.identity.domain.events import (
    UserDeactivated,
    UserPasswordChanged,
    UserRegistered,
)
from basis.modules.identity.domain.models import User
from basis.modules.identity.domain.value_objects import (
    COMMON_PASSWORDS,
    Email,
    PasswordPolicy,
    PlainPassword,
    Role,
)

MOMENT = datetime(2026, 3, 10, 9, 30, tzinfo=UTC)


class TestEmail:
    @pytest.mark.parametrize(
        "raw",
        ["ana@basis.dev", "  ANA@BASIS.DEV ", "a.b+c-d@sub.domain.com.br"],
    )
    def test_valid_emails_are_normalized(self, raw: str) -> None:
        assert Email(raw).value == raw.strip().lower()

    @pytest.mark.parametrize(
        "raw",
        ["", "no-at-sign", "ana@", "@basis.dev", "ana@basis", "ana space@basis.dev"],
    )
    def test_invalid_emails_are_rejected(self, raw: str) -> None:
        with pytest.raises(ValidationError):
            Email(raw)

    def test_email_too_long_is_rejected(self) -> None:
        local = "a" * 250
        with pytest.raises(ValidationError, match="at most 254"):
            Email(f"{local}@basis.dev")

    def test_domain_property(self) -> None:
        assert Email("ana@insper.edu.br").domain == "insper.edu.br"


class TestPasswordPolicy:
    @pytest.mark.parametrize(
        "password",
        ["s3nh4-forte", "Basis2026!", "uma-frase-longa-1"],
    )
    def test_accepts_strong_passwords(self, password: str) -> None:
        PasswordPolicy().validate(PlainPassword(password))

    @pytest.mark.parametrize(
        ("password", "reason"),
        [
            ("curta1", "at least 10 characters"),
            ("somenteletras", "at least one digit"),
            ("1234567890", "at least one letter"),
            (next(iter(COMMON_PASSWORDS)), "commonly used password"),
        ],
    )
    def test_rejects_weak_passwords(self, password: str, reason: str) -> None:
        with pytest.raises(ValidationError) as exc_info:
            PasswordPolicy().validate(PlainPassword(password))
        assert reason in str(exc_info.value.details)

    def test_plain_password_never_leaks_in_repr(self) -> None:
        password = PlainPassword("super-secret-1")
        assert "super-secret-1" not in repr(password)
        assert "super-secret-1" not in str(password)

    def test_empty_password_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must not be empty"):
            PlainPassword("")


class TestUserAggregate:
    def _register(self, clock: FrozenClock, role: Role = Role.ADVISOR) -> User:
        return User.register(
            email=Email("ana@basis.dev"),
            display_name="  Ana   Souza ",
            role=role,
            password_hash="hash-1",
            clock=clock,
        )

    def test_registration_normalizes_name_and_records_event(self) -> None:
        user = self._register(FrozenClock(MOMENT))
        assert user.display_name == "Ana Souza"
        assert user.is_active is True
        assert user.created_at == MOMENT

        events = user.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, UserRegistered)
        assert event.user_id == user.id
        assert event.email == "ana@basis.dev"

    @pytest.mark.parametrize("name", ["", "A", "x" * 121])
    def test_invalid_names_are_rejected(self, name: str) -> None:
        with pytest.raises(ValidationError):
            self._register_name(name)

    def _register_name(self, name: str) -> User:
        return User.register(
            email=Email("ana@basis.dev"),
            display_name=name,
            role=Role.ADVISOR,
            password_hash="hash-1",
            clock=FrozenClock(MOMENT),
        )

    def test_change_password_updates_timestamp_and_records_event(self) -> None:
        clock = FrozenClock(MOMENT)
        user = self._register(clock)
        user.pull_events()

        clock.advance(timedelta(hours=1))
        user.change_password("hash-2", clock=clock)

        assert user.password_hash == "hash-2"
        assert user.updated_at == MOMENT + timedelta(hours=1)
        events = user.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], UserPasswordChanged)

    def test_change_password_to_same_hash_is_rejected(self) -> None:
        user = self._register(FrozenClock(MOMENT))
        with pytest.raises(InvariantViolationError, match="must differ"):
            user.change_password("hash-1", clock=FrozenClock(MOMENT))

    def test_deactivate_is_idempotent_and_records_event_once(self) -> None:
        clock = FrozenClock(MOMENT)
        user = self._register(clock)
        user.pull_events()

        user.deactivate(clock=clock)
        user.deactivate(clock=clock)

        assert user.is_active is False
        events = user.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], UserDeactivated)

    def test_activate_is_idempotent(self) -> None:
        clock = FrozenClock(MOMENT)
        user = self._register(clock)
        user.deactivate(clock=clock)
        user.activate(clock=clock)
        user.activate(clock=clock)
        assert user.is_active is True

    def test_role_capabilities(self) -> None:
        assert Role.ADMIN.can_manage_clients()
        assert Role.ADVISOR.can_manage_clients()
        assert not Role.VIEWER.can_manage_clients()
        assert Role.ADMIN.is_admin
        assert not Role.ADVISOR.is_admin

    def test_deactivated_user_cannot_manage_clients(self) -> None:
        clock = FrozenClock(MOMENT)
        user = self._register(clock, role=Role.ADMIN)
        user.deactivate(clock=clock)
        assert not user.can_manage_clients()
