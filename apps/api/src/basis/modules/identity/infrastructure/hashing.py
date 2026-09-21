"""Argon2id password hashing (OWASP-recommended parameters by default)."""

from __future__ import annotations

import secrets

from argon2 import PasswordHasher as Argon2PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from basis.modules.identity.domain.value_objects import PlainPassword


class Argon2idHasher:
    """Salted, memory-hard password hashing with transparent rehash support."""

    def __init__(
        self,
        *,
        time_cost: int = 3,
        memory_cost_kib: int = 65536,
        parallelism: int = 4,
        hash_len: int = 32,
        salt_len: int = 16,
    ) -> None:
        self._hasher = Argon2PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost_kib,
            parallelism=parallelism,
            hash_len=hash_len,
            salt_len=salt_len,
        )
        self._dummy_hash = self._hasher.hash(secrets.token_urlsafe(32))

    def hash(self, password: PlainPassword) -> str:
        return self._hasher.hash(password.value)

    def verify(self, password: PlainPassword, password_hash: str) -> bool:
        try:
            return bool(self._hasher.verify(password_hash, password.value))
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, password_hash: str) -> bool:
        try:
            return bool(self._hasher.check_needs_rehash(password_hash))
        except InvalidHashError:
            return True

    def dummy_hash(self) -> str:
        """A hash of a random value, used to equalise failed-login timing."""
        return self._dummy_hash


__all__ = ["Argon2idHasher"]
