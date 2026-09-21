"""Unit tests for clients domain rules (no I/O, no framework)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from basis.kernel.domain.clock import FrozenClock
from basis.kernel.domain.errors import InvariantViolationError, ValidationError
from basis.modules.clients.domain.events import (
    ClientArchived,
    ClientRegistered,
    ClientSuitabilityAssessed,
)
from basis.modules.clients.domain.models import Client
from basis.modules.clients.domain.value_objects import (
    ClientStatus,
    ContactEmail,
    PersonName,
    SuitabilityAssessment,
    SuitabilityProfile,
    TaxId,
    TaxIdKind,
)

MOMENT = datetime(2026, 3, 10, 9, 30, tzinfo=UTC)

VALID_CPFS = ["52998224725", "11144477735", "12345678909"]
VALID_CNPJS = ["11222333000181", "04252011000110"]


class TestTaxId:
    @pytest.mark.parametrize("raw", VALID_CPFS)
    def test_valid_cpfs_are_accepted(self, raw: str) -> None:
        tax_id = TaxId(raw)
        assert tax_id.value == raw
        assert tax_id.kind is TaxIdKind.CPF

    @pytest.mark.parametrize("raw", VALID_CNPJS)
    def test_valid_cnpjs_are_accepted(self, raw: str) -> None:
        tax_id = TaxId(raw)
        assert tax_id.value == raw
        assert tax_id.kind is TaxIdKind.CNPJ

    def test_punctuation_is_normalized(self) -> None:
        assert TaxId("529.982.247-25").value == "52998224725"
        assert TaxId("11.222.333/0001-81").value == "11222333000181"

    def test_leading_zero_cnpj_is_preserved(self) -> None:
        assert TaxId("04.252.011/0001-10").value == "04252011000110"

    def test_masked_cpf(self) -> None:
        assert TaxId("52998224725").masked == "***.***.247-25"

    def test_masked_cnpj(self) -> None:
        assert TaxId("11222333000181").masked == "**.***.***/****-81"

    def test_str_never_reveals_the_full_document(self) -> None:
        assert str(TaxId("52998224725")) == "***.***.247-25"

    @pytest.mark.parametrize(
        "raw",
        ["52998224724", "11144477736", "12345678908", "11222333000182", "04252011000111"],
    )
    def test_invalid_check_digits_are_rejected(self, raw: str) -> None:
        with pytest.raises(ValidationError, match="check digits"):
            TaxId(raw)

    @pytest.mark.parametrize(
        "raw",
        ["11111111111", "00000000000", "99999999999999", "22222222222"],
    )
    def test_repeated_digits_are_rejected(self, raw: str) -> None:
        with pytest.raises(ValidationError, match="repeated digit"):
            TaxId(raw)

    @pytest.mark.parametrize(
        "raw",
        ["", "123", "1234567890", "1234567890123", "123456789012345", "not-a-tax-id"],
    )
    def test_invalid_lengths_are_rejected(self, raw: str) -> None:
        with pytest.raises(ValidationError, match="CPF"):
            TaxId(raw)

    def test_error_details_include_the_length(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            TaxId("123")
        assert exc_info.value.details["length"] == 3


class TestPersonName:
    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Ana Souza", "Ana Souza"),
            ("  Ana   Souza  ", "Ana Souza"),
            ("Ana-Maria D'Ávila", "Ana-Maria D'Ávila"),
            ("Ædán", "Ædán"),
        ],
    )
    def test_valid_names_are_normalized(self, raw: str, expected: str) -> None:
        assert PersonName(raw).value == expected

    @pytest.mark.parametrize("raw", ["", "A", "  ", "x" * 121])
    def test_invalid_lengths_are_rejected(self, raw: str) -> None:
        with pytest.raises(ValidationError, match="between"):
            PersonName(raw)

    @pytest.mark.parametrize("raw", ["Ana 2", "12345", "Ana 3rd"])
    def test_digits_are_rejected(self, raw: str) -> None:
        with pytest.raises(ValidationError, match="digits"):
            PersonName(raw)

    @pytest.mark.parametrize("raw", ["---", "!!!"])
    def test_names_without_letters_are_rejected(self, raw: str) -> None:
        with pytest.raises(ValidationError, match="letter"):
            PersonName(raw)


class TestContactEmail:
    @pytest.mark.parametrize(
        "raw", ["ana@basis.dev", "  ANA@BASIS.DEV ", "a.b+c-d@sub.domain.com.br"]
    )
    def test_valid_emails_are_normalized(self, raw: str) -> None:
        assert ContactEmail(raw).value == raw.strip().lower()

    @pytest.mark.parametrize(
        "raw", ["", "no-at-sign", "ana@", "@basis.dev", "ana@basis", "ana space@basis.dev"]
    )
    def test_invalid_emails_are_rejected(self, raw: str) -> None:
        with pytest.raises(ValidationError):
            ContactEmail(raw)

    def test_email_too_long_is_rejected(self) -> None:
        local = "a" * 250
        with pytest.raises(ValidationError, match="at most 254"):
            ContactEmail(f"{local}@basis.dev")

    def test_domain_property(self) -> None:
        assert ContactEmail("ana@insper.edu.br").domain == "insper.edu.br"


class TestSuitabilityAssessment:
    def test_neutral_assessment_sits_in_the_middle(self) -> None:
        assessment = SuitabilityAssessment.neutral()
        assert assessment.score == 50
        assert assessment.profile is SuitabilityProfile.MODERATE

    @pytest.mark.parametrize(
        ("answers", "score", "profile"),
        [
            ((0, 0, 0, 0, 0), 0, SuitabilityProfile.CONSERVATIVE),
            ((1, 1, 1, 2, 1), 30, SuitabilityProfile.CONSERVATIVE),
            ((1, 1, 1, 2, 2), 35, SuitabilityProfile.MODERATE),
            ((3, 3, 3, 2, 2), 65, SuitabilityProfile.MODERATE),
            ((3, 3, 3, 3, 2), 70, SuitabilityProfile.AGGRESSIVE),
            ((4, 4, 4, 4, 4), 100, SuitabilityProfile.AGGRESSIVE),
        ],
    )
    def test_profile_thresholds(
        self, answers: tuple[int, ...], score: int, profile: SuitabilityProfile
    ) -> None:
        assessment = SuitabilityAssessment(answers=answers)
        assert assessment.score == score
        assert assessment.profile is profile

    def test_ten_answers_are_normalized_to_the_same_scale(self) -> None:
        assessment = SuitabilityAssessment(answers=(2,) * 10)
        assert assessment.score == 50
        assert assessment.profile is SuitabilityProfile.MODERATE

    def test_answers_are_immutable(self) -> None:
        assessment = SuitabilityAssessment(answers=[1, 2, 3, 4, 0])
        assert assessment.answers == (1, 2, 3, 4, 0)

    @pytest.mark.parametrize("answers", [(2,) * 4, (2,) * 11, ()])
    def test_answer_count_outside_bounds_is_rejected(self, answers: tuple[int, ...]) -> None:
        with pytest.raises(ValidationError, match="between"):
            SuitabilityAssessment(answers=answers)

    @pytest.mark.parametrize("answer", [-1, 5, 10])
    def test_out_of_range_answers_are_rejected(self, answer: int) -> None:
        with pytest.raises(ValidationError, match="between 0 and"):
            SuitabilityAssessment(answers=(1, 2, answer, 3, 0))


def make_client(
    clock: FrozenClock,
    *,
    name: str = "  Ana   Souza ",
    email: str = "ana@basis.dev",
    tax_id: str = "52998224725",
    answers: tuple[int, ...] = (4, 4, 4, 4, 4),
    notes: str | None = "Private banking",
) -> Client:
    return Client.register(
        name=PersonName(name),
        email=ContactEmail(email),
        tax_id=TaxId(tax_id),
        assessment=SuitabilityAssessment(answers=answers),
        notes=notes,
        clock=clock,
    )


class TestClientAggregate:
    def test_registration_normalizes_and_records_event(self) -> None:
        client = make_client(FrozenClock(MOMENT))
        assert str(client.name) == "Ana Souza"
        assert client.status is ClientStatus.ACTIVE
        assert client.suitability is SuitabilityProfile.AGGRESSIVE
        assert client.suitability_score == 100
        assert client.created_at == MOMENT
        assert client.updated_at == MOMENT

        events = client.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ClientRegistered)
        assert event.client_id == client.id
        assert event.client_name == "Ana Souza"
        assert event.tax_id_masked == "***.***.247-25"
        assert event.suitability == "aggressive"
        assert event.suitability_score == 100

    def test_registration_rejects_long_notes(self) -> None:
        with pytest.raises(ValidationError, match="at most 500"):
            make_client(FrozenClock(MOMENT), notes="x" * 501)

    def test_blank_notes_are_normalized_to_none(self) -> None:
        client = make_client(FrozenClock(MOMENT), notes="   ")
        assert client.notes is None

    def test_update_details_changes_fields_and_timestamp(self) -> None:
        clock = FrozenClock(MOMENT)
        client = make_client(clock)
        client.pull_events()

        clock.advance(timedelta(days=1))
        client.update_details(
            name=PersonName("Ana Maria Souza"),
            email=ContactEmail("ana.maria@basis.dev"),
            notes=None,
            clock=clock,
        )

        assert str(client.name) == "Ana Maria Souza"
        assert str(client.email) == "ana.maria@basis.dev"
        assert client.notes is None
        assert client.updated_at == MOMENT + timedelta(days=1)
        assert client.pull_events() == []

    def test_assess_suitability_updates_profile_and_records_event(self) -> None:
        clock = FrozenClock(MOMENT)
        client = make_client(clock)
        client.pull_events()

        clock.advance(timedelta(days=2))
        client.assess_suitability(SuitabilityAssessment(answers=(0, 0, 0, 0, 0)), clock=clock)

        assert client.suitability is SuitabilityProfile.CONSERVATIVE
        assert client.suitability_score == 0
        assert client.updated_at == MOMENT + timedelta(days=2)
        events = client.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ClientSuitabilityAssessed)
        assert events[0].suitability == "conservative"

    def test_archive_is_idempotent_and_records_event_once(self) -> None:
        clock = FrozenClock(MOMENT)
        client = make_client(clock)
        client.pull_events()

        client.archive(clock=clock)
        client.archive(clock=clock)

        assert client.status is ClientStatus.ARCHIVED
        events = client.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ClientArchived)

    def test_archived_client_cannot_be_updated(self) -> None:
        clock = FrozenClock(MOMENT)
        client = make_client(clock)
        client.archive(clock=clock)

        with pytest.raises(InvariantViolationError, match="archived"):
            client.update_details(
                name=PersonName("Outra Pessoa"),
                email=ContactEmail("outra@basis.dev"),
                notes=None,
                clock=clock,
            )

    def test_archived_client_cannot_be_reassessed(self) -> None:
        clock = FrozenClock(MOMENT)
        client = make_client(clock)
        client.archive(clock=clock)

        with pytest.raises(InvariantViolationError, match="archived"):
            client.assess_suitability(SuitabilityAssessment(answers=(0, 0, 0, 0, 0)), clock=clock)

    def test_reactivate_is_idempotent_and_restores_updates(self) -> None:
        clock = FrozenClock(MOMENT)
        client = make_client(clock)
        client.archive(clock=clock)
        client.pull_events()

        client.reactivate(clock=clock)
        client.reactivate(clock=clock)

        assert client.status is ClientStatus.ACTIVE
        assert client.pull_events() == []
        client.update_details(
            name=PersonName("Ana Souza"),
            email=ContactEmail("ana@basis.dev"),
            notes="ok",
            clock=clock,
        )
        assert client.notes == "ok"
