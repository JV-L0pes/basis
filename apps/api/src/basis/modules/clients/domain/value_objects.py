"""Clients value objects: tax ids, names, suitability and status."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
import re
from typing import ClassVar

from basis.kernel.domain.errors import ValidationError

CPF_LENGTH = 11
CNPJ_LENGTH = 14
NAME_MAX_LENGTH = 120
NAME_MIN_LENGTH = 2
EMAIL_MAX_LENGTH = 254
NOTES_MAX_LENGTH = 500

_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9!#$%&'*+/=?^_`{|}~.-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)
_NON_DIGITS = re.compile(r"\D")


class TaxIdKind(StrEnum):
    """Brazilian tax identifier kinds."""

    CPF = "cpf"
    CNPJ = "cnpj"


def _check_digit(digits: Sequence[int], weights: Sequence[int]) -> int:
    total = sum(digit * weight for digit, weight in zip(digits, weights, strict=True))
    remainder = total % 11
    return 0 if remainder < 2 else 11 - remainder


def _is_repeated(digits: str) -> bool:
    return len(set(digits)) == 1


@dataclass(frozen=True, slots=True)
class TaxId:
    """A validated Brazilian CPF (individual) or CNPJ (company) number.

    Validation uses the official mod-11 check-digit algorithm, so invalid
    documents are rejected before they ever reach the database.
    """

    value: str

    CPF_WEIGHTS: ClassVar[tuple[int, ...]] = (10, 9, 8, 7, 6, 5, 4, 3, 2)
    CPF_WEIGHTS_WITH_DV: ClassVar[tuple[int, ...]] = (11, 10, 9, 8, 7, 6, 5, 4, 3, 2)
    CNPJ_WEIGHTS: ClassVar[tuple[int, ...]] = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    CNPJ_WEIGHTS_WITH_DV: ClassVar[tuple[int, ...]] = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)

    def __post_init__(self) -> None:
        digits = _NON_DIGITS.sub("", self.value)
        if len(digits) not in (CPF_LENGTH, CNPJ_LENGTH):
            raise ValidationError(
                "Tax id must have 11 (CPF) or 14 (CNPJ) digits",
                details={"length": len(digits), "value": self.value},
            )
        if _is_repeated(digits):
            raise ValidationError(
                "Tax id cannot be a repeated digit sequence", details={"value": self.value}
            )

        numbers = [int(character) for character in digits]
        if len(digits) == CPF_LENGTH:
            body = numbers[:9]
            weights = self.CPF_WEIGHTS
            weights_with_dv = self.CPF_WEIGHTS_WITH_DV
        else:
            body = numbers[:12]
            weights = self.CNPJ_WEIGHTS
            weights_with_dv = self.CNPJ_WEIGHTS_WITH_DV

        first = _check_digit(body, weights)
        if first != numbers[len(body)]:
            raise ValidationError(
                "Tax id check digits are invalid",
                details={"digit": 1, "value": self.value},
            )
        second = _check_digit([*body, first], weights_with_dv)
        if second != numbers[len(body) + 1]:
            raise ValidationError(
                "Tax id check digits are invalid",
                details={"digit": 2, "value": self.value},
            )

        object.__setattr__(self, "value", digits)

    @property
    def kind(self) -> TaxIdKind:
        return TaxIdKind.CPF if len(self.value) == CPF_LENGTH else TaxIdKind.CNPJ

    @property
    def masked(self) -> str:
        """Return a partially hidden representation, safe for logs and lists."""
        if self.kind is TaxIdKind.CPF:
            return f"***.***.{self.value[6:9]}-{self.value[9:]}"
        return f"**.***.***/****-{self.value[12:]}"

    @property
    def formatted(self) -> str:
        if self.kind is TaxIdKind.CPF:
            return f"{self.value[:3]}.{self.value[3:6]}.{self.value[6:9]}-{self.value[9:]}"
        return (
            f"{self.value[:2]}.{self.value[2:5]}.{self.value[5:8]}"
            f"/{self.value[8:12]}-{self.value[12:]}"
        )

    def __str__(self) -> str:
        return self.masked


@dataclass(frozen=True, slots=True)
class PersonName:
    """A person's display name."""

    value: str

    def __post_init__(self) -> None:
        normalized = " ".join(self.value.split())
        if len(normalized) > NAME_MAX_LENGTH or len(normalized) < NAME_MIN_LENGTH:
            raise ValidationError(
                f"Name must be between {NAME_MIN_LENGTH} and {NAME_MAX_LENGTH} characters",
                details={"length": len(normalized)},
            )
        if any(character.isdigit() for character in normalized):
            raise ValidationError("Name must not contain digits")
        if not any(character.isalpha() for character in normalized):
            raise ValidationError("Name must contain at least one letter")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ContactEmail:
    """E-mail used to contact a client."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if len(normalized) > EMAIL_MAX_LENGTH:
            raise ValidationError(
                f"E-mail must be at most {EMAIL_MAX_LENGTH} characters",
                details={"length": len(normalized)},
            )
        if not _EMAIL_PATTERN.match(normalized):
            raise ValidationError("Invalid e-mail address", details={"email": self.value})
        object.__setattr__(self, "value", normalized)

    @property
    def domain(self) -> str:
        return self.value.rsplit("@", 1)[-1]

    def __str__(self) -> str:
        return self.value


class SuitabilityProfile(StrEnum):
    """Risk profile derived from the suitability questionnaire."""

    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


MIN_ANSWERS = 5
MAX_ANSWERS = 10
MAX_ANSWER_SCORE = 4
MAX_SCORE = 100
MODERATE_THRESHOLD = 35
AGGRESSIVE_THRESHOLD = 70


@dataclass(frozen=True, slots=True)
class SuitabilityAssessment:
    """Answers to the suitability questionnaire, reduced to a risk profile.

    Each answer scores 0..4; the total is normalised to 0..100. Scores below
    ``MODERATE_THRESHOLD`` classify the investor as conservative, below
    ``AGGRESSIVE_THRESHOLD`` as moderate, and the rest as aggressive.
    """

    answers: Sequence[int]

    def __post_init__(self) -> None:
        answers = tuple(self.answers)
        if not (MIN_ANSWERS <= len(answers) <= MAX_ANSWERS):
            raise ValidationError(
                f"Suitability requires between {MIN_ANSWERS} and {MAX_ANSWERS} answers",
                details={"answers": len(answers)},
            )
        if any(not 0 <= answer <= MAX_ANSWER_SCORE for answer in answers):
            raise ValidationError(
                f"Each answer must be between 0 and {MAX_ANSWER_SCORE}",
                details={"answers": list(answers)},
            )
        object.__setattr__(self, "answers", answers)

    @classmethod
    def from_scores(cls, answers: list[int]) -> SuitabilityAssessment:
        return cls(answers=tuple(answers))

    @classmethod
    def neutral(cls) -> SuitabilityAssessment:
        """A 50-point, moderate assessment (unanswered questionnaire default)."""
        return cls(answers=(2, 2, 2, 2, 2))

    @property
    def score(self) -> int:
        maximum = len(self.answers) * MAX_ANSWER_SCORE
        return round(sum(self.answers) / maximum * MAX_SCORE)

    @property
    def profile(self) -> SuitabilityProfile:
        if self.score < MODERATE_THRESHOLD:
            return SuitabilityProfile.CONSERVATIVE
        if self.score < AGGRESSIVE_THRESHOLD:
            return SuitabilityProfile.MODERATE
        return SuitabilityProfile.AGGRESSIVE


class ClientStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


__all__ = [
    "AGGRESSIVE_THRESHOLD",
    "CNPJ_LENGTH",
    "CPF_LENGTH",
    "EMAIL_MAX_LENGTH",
    "MAX_ANSWERS",
    "MAX_ANSWER_SCORE",
    "MIN_ANSWERS",
    "MODERATE_THRESHOLD",
    "NAME_MAX_LENGTH",
    "NOTES_MAX_LENGTH",
    "ClientStatus",
    "ContactEmail",
    "PersonName",
    "SuitabilityAssessment",
    "SuitabilityProfile",
    "TaxId",
    "TaxIdKind",
]
