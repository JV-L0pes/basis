"""Identity value objects: e-mail, password policy and roles."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import re

from basis.kernel.domain.errors import ValidationError

EMAIL_MAX_LENGTH = 254
_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9!#$%&'*+/=?^_`{|}~.-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)

DISPLAY_NAME_MIN_LENGTH = 2
DISPLAY_NAME_MAX_LENGTH = 120

# A small deny-list of passwords that must never be accepted. A production
# deployment would back this with a larger breached-password corpus.
COMMON_PASSWORDS = frozenset(
    {
        "1234567890",
        "password12",
        "qwertyuiop",
        "senha12345",
        "administrator",
        "letmein123",
    }
)


@dataclass(frozen=True, slots=True)
class Email:
    """A normalised, validated e-mail address."""

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


@dataclass(frozen=True, slots=True)
class PlainPassword:
    """A password in clear text. Never persisted, logged or serialised."""

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValidationError("Password must not be empty")
        if len(self.value) > 128:
            raise ValidationError("Password must be at most 128 characters")

    def __repr__(self) -> str:
        return "PlainPassword(***)"

    __str__ = __repr__


class PasswordPolicy:
    """Domain service that enforces the password strength policy."""

    min_length: int = 10

    def validate(self, password: PlainPassword) -> None:
        problems: list[str] = []
        if len(password.value) < self.min_length:
            problems.append(f"at least {self.min_length} characters")
        if not any(character.isalpha() for character in password.value):
            problems.append("at least one letter")
        if not any(character.isdigit() for character in password.value):
            problems.append("at least one digit")
        if password.value.lower() in COMMON_PASSWORDS:
            problems.append("not a commonly used password")
        if problems:
            raise ValidationError(
                "Password does not meet the security policy",
                details={"requirements": problems},
            )


class Role(StrEnum):
    """Authorisation roles. Ordered from most to least privileged."""

    ADMIN = "admin"
    ADVISOR = "advisor"
    VIEWER = "viewer"

    @property
    def is_admin(self) -> bool:
        return self is Role.ADMIN

    def can_manage_clients(self) -> bool:
        return self in (Role.ADMIN, Role.ADVISOR)


__all__ = [
    "COMMON_PASSWORDS",
    "DISPLAY_NAME_MAX_LENGTH",
    "DISPLAY_NAME_MIN_LENGTH",
    "EMAIL_MAX_LENGTH",
    "Email",
    "PasswordPolicy",
    "PlainPassword",
    "Role",
]
