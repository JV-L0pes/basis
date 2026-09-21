"""Defensive helpers for parsing untrusted JSON payloads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation


def as_mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def as_sequence(value: object) -> Sequence[object]:
    return value if isinstance(value, (list, tuple)) else ()


def as_str(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def as_decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        cleaned = value.strip().replace(".", "").replace(",", ".") if "," in value else value.strip()
        try:
            return Decimal(cleaned)
        except InvalidOperation:
            return None
    return None


def as_int(value: object) -> int | None:
    decimal_value = as_decimal(value)
    if decimal_value is None:
        return None
    try:
        return int(decimal_value)
    except (ValueError, OverflowError):
        return None


def parse_iso_date(value: object) -> date | None:
    """Parse ``YYYY-MM-DD`` or a full ISO-8601 timestamp into a date (UTC)."""
    raw = as_str(value)
    if raw is None:
        return None
    try:
        if "T" in raw or " " in raw:
            normalized = raw.replace("Z", "+00:00")
            return datetime.fromisoformat(normalized).astimezone(UTC).date()
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def parse_datetime(value: object) -> datetime | None:
    """Parse an ISO-8601 string or an epoch timestamp (seconds) into a UTC datetime."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(float(value), tz=UTC)
    raw = as_str(value)
    if raw is None:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def parse_bcb_date(value: object) -> date | None:
    """BCB SGS returns dates as ``DD/MM/YYYY``."""
    raw = as_str(value)
    if raw is None:
        return None
    try:
        return datetime.strptime(raw, "%d/%m/%Y").replace(tzinfo=UTC).date()
    except ValueError:
        return None


__all__ = [
    "as_decimal",
    "as_int",
    "as_mapping",
    "as_sequence",
    "as_str",
    "parse_bcb_date",
    "parse_datetime",
    "parse_iso_date",
]
