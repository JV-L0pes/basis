"""Shared kernel vocabulary for asset classification.

``AssetClass`` is deliberately part of the shared kernel: portfolio management,
market data and analytics all need the same ubiquitous language for asset
classes, so it is not owned by any single bounded context.
"""

from __future__ import annotations

from enum import StrEnum


class AssetClass(StrEnum):
    """Broad asset classes used across the platform."""

    EQUITY = "equity"
    FIXED_INCOME = "fixed_income"
    FUND = "fund"
    ETF = "etf"
    REAL_ESTATE = "real_estate"
    CRYPTO = "crypto"
    CASH = "cash"
    COMMODITY = "commodity"
    OTHER = "other"


INCOME_CLASSES: frozenset[AssetClass] = frozenset({AssetClass.FIXED_INCOME, AssetClass.CASH})
"""Classes whose primary return driver is interest, used by risk scoring."""


class RiskLevel(StrEnum):
    """Discretionary risk bucket attached to an instrument."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


__all__ = ["INCOME_CLASSES", "AssetClass", "RiskLevel"]
