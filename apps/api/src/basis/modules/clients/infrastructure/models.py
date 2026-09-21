"""SQLAlchemy persistence models for the clients context."""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from basis.kernel.infrastructure.db import Base, TimestampMixin, UuidPrimaryKeyMixin


class ClientRow(Base, UuidPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "clients"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), nullable=False, index=True)
    tax_id: Mapped[str] = mapped_column(String(14), unique=True, index=True, nullable=False)
    tax_id_kind: Mapped[str] = mapped_column(String(4), nullable=False)
    suitability: Mapped[str] = mapped_column(String(20), nullable=False)
    suitability_score: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(String(500))


__all__ = ["ClientRow"]
