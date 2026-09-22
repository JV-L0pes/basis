"""Application settings, loaded from the environment with the ``BASIS_`` prefix.

Nested settings use a double underscore, e.g. ``BASIS_AUTH__ACCESS_TOKEN_TTL_MINUTES=30``.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "test", "staging", "production"]

# Monorepo layout: apps/api/src/basis/config.py -> repository root.
_REPO_ROOT = Path(__file__).resolve().parents[4]
_ENV_FILES = (str(_REPO_ROOT / ".env"), ".env")


class AuthSettings(BaseSettings):
    """Authentication and token policy."""

    algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    access_token_ttl_minutes: int = Field(default=15, ge=1, le=24 * 60)
    refresh_token_ttl_days: int = Field(default=14, ge=1, le=365)
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: SecretStr | None = None

    # Argon2id parameters (OWASP minimum: 19 MiB, t=2, p=1).
    argon2_time_cost: int = Field(default=3, ge=1, le=20)
    argon2_memory_cost_kib: int = Field(default=65536, ge=8, le=1_048_576)
    argon2_parallelism: int = Field(default=4, ge=1, le=16)


class MarketDataSettings(BaseSettings):
    """Market data providers and caching policy."""

    brapi_token: SecretStr | None = None
    quote_cache_ttl_seconds: int = Field(default=60, ge=0, le=86_400)
    http_timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    allow_live_providers: bool = True
    max_history_days: int = Field(default=1825, ge=30, le=3650)


class Settings(BaseSettings):
    """Root settings object. Use :func:`get_settings` to obtain the singleton."""

    model_config = SettingsConfigDict(
        env_prefix="BASIS_",
        env_nested_delimiter="__",
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    app_name: str = "Basis API"
    environment: Environment = "local"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    port: int = Field(default=8000, ge=1, le=65535, description="Dev server port (python -m basis)")

    secret_key: SecretStr = SecretStr("insecure-development-secret-change-me")
    cors_origins: list[str] = ["http://localhost:5173"]

    database_url: str = "postgresql+psycopg://basis:basis@localhost:5432/basis"
    test_database_url: str | None = None
    db_echo: bool = False

    auth: AuthSettings = AuthSettings()
    market_data: MarketDataSettings = MarketDataSettings()

    @property
    def is_local(self) -> bool:
        return self.environment in ("local", "test")

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
