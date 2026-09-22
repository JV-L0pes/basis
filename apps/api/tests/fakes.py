"""In-memory doubles for domain ports, used by fast unit tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
import hashlib
from uuid import UUID

from basis.kernel.application.pagination import decode_cursor
from basis.kernel.domain.assets import AssetClass
from basis.kernel.domain.currency import Currency
from basis.kernel.domain.errors import ExternalServiceError, NotFoundError
from basis.kernel.domain.money import Money
from basis.modules.clients.domain.models import Client
from basis.modules.clients.domain.ports import ClientCursor, ClientSummary
from basis.modules.clients.domain.value_objects import ClientStatus, TaxId
from basis.modules.identity.domain.models import User
from basis.modules.identity.domain.ports import (
    AccessTokenClaims,
    IssuedToken,
    RefreshTokenRecord,
)
from basis.modules.identity.domain.value_objects import Email, PlainPassword, Role
from basis.modules.market_data.domain.models import Instrument, PricePoint
from basis.modules.market_data.domain.ports import (
    IndexPointView,
    InstrumentSummary,
    QuoteView,
)
from basis.modules.market_data.domain.value_objects import MacroSeriesCode


class InMemoryUserRepository:
    def __init__(self) -> None:
        self.users: dict[UUID, User] = {}

    async def get(self, user_id: UUID) -> User | None:
        return self.users.get(user_id)

    async def get_by_email(self, email: Email) -> User | None:
        return next((user for user in self.users.values() if user.email == email), None)

    async def add(self, user: User) -> None:
        self.users[user.id] = user

    async def update(self, user: User) -> None:
        self.users[user.id] = user

    async def count(self) -> int:
        return len(self.users)


class InMemoryRefreshTokenRepository:
    def __init__(self) -> None:
        self.records: dict[str, RefreshTokenRecord] = {}

    async def add(self, record: RefreshTokenRecord) -> None:
        self.records[record.token_digest] = record

    async def get_by_digest(self, digest: str) -> RefreshTokenRecord | None:
        return self.records.get(digest)

    async def update(self, record: RefreshTokenRecord) -> None:
        self.records[record.token_digest] = record

    async def revoke_all_for_user(self, user_id: UUID, *, at: datetime) -> int:
        revoked = 0
        for record in self.records.values():
            if record.user_id == user_id and record.revoked_at is None:
                record.revoked_at = at
                revoked += 1
        return revoked

    async def list_active_for_user(
        self, user_id: UUID, *, now: datetime
    ) -> Sequence[RefreshTokenRecord]:
        return [
            record
            for record in self.records.values()
            if record.user_id == user_id and record.is_usable(now)
        ]


class InMemoryClientRepository:
    """Mirrors the keyset-pagination contract of the SQLAlchemy repository."""

    def __init__(self) -> None:
        self.clients: dict[UUID, Client] = {}

    async def get(self, client_id: UUID) -> Client | None:
        return self.clients.get(client_id)

    async def get_by_tax_id(self, tax_id: TaxId) -> Client | None:
        return next((client for client in self.clients.values() if client.tax_id == tax_id), None)

    async def add(self, client: Client) -> None:
        self.clients[client.id] = client

    async def update(self, client: Client) -> None:
        self.clients[client.id] = client

    async def list_page(
        self,
        *,
        limit: int,
        cursor: ClientCursor | None = None,
        query: str | None = None,
        status: ClientStatus | None = None,
    ) -> tuple[Sequence[Client], bool]:
        items = sorted(
            self.clients.values(),
            key=lambda client: (client.created_at, client.id),
            reverse=True,
        )
        if status is not None:
            items = [client for client in items if client.status is status]
        if query:
            needle = query.lower()
            items = [
                client
                for client in items
                if needle in client.name.value.lower() or needle in client.email.value
            ]
        if cursor is not None:
            items = [
                client
                for client in items
                if (client.created_at, client.id) < (cursor.created_at, cursor.id)
            ]
        has_more = len(items) > limit
        return items[:limit], has_more

    async def count_by_status(self) -> Mapping[ClientStatus, int]:
        counts: dict[ClientStatus, int] = {}
        for client in self.clients.values():
            counts[client.status] = counts.get(client.status, 0) + 1
        return counts


class InMemoryClientDirectory:
    def __init__(self, repository: InMemoryClientRepository) -> None:
        self._repository = repository

    async def get_client_summary(self, client_id: UUID) -> ClientSummary | None:
        client = await self._repository.get(client_id)
        if client is None:
            return None
        return ClientSummary(
            id=client.id,
            name=client.name.value,
            status=str(client.status),
            suitability=str(client.suitability),
        )

    async def require_client(self, client_id: UUID) -> ClientSummary:
        summary = await self.get_client_summary(client_id)
        if summary is None:
            raise NotFoundError("Client not found", details={"client_id": str(client_id)})
        return summary


class InMemoryInstrumentRepository:
    """Mirrors the keyset-pagination contract of the SQLAlchemy repository."""

    def __init__(self) -> None:
        self.instruments: dict[UUID, Instrument] = {}

    async def get(self, instrument_id: UUID) -> Instrument | None:
        return self.instruments.get(instrument_id)

    async def get_by_symbol(self, symbol: str) -> Instrument | None:
        normalized = symbol.strip().upper()
        return next(
            (
                instrument
                for instrument in self.instruments.values()
                if str(instrument.symbol) == normalized
            ),
            None,
        )

    async def add(self, instrument: Instrument) -> None:
        self.instruments[instrument.id] = instrument

    async def update(self, instrument: Instrument) -> None:
        self.instruments[instrument.id] = instrument

    async def list_page(
        self,
        *,
        limit: int,
        cursor: str | None = None,
        query: str | None = None,
        asset_class: AssetClass | None = None,
    ) -> tuple[Sequence[Instrument], bool]:
        items = sorted(
            (item for item in self.instruments.values() if item.is_active),
            key=lambda item: str(item.symbol),
        )
        if asset_class is not None:
            items = [item for item in items if item.asset_class is asset_class]
        if query:
            needle = query.lower()
            items = [
                item
                for item in items
                if needle in str(item.symbol).lower() or needle in item.name.lower()
            ]
        if cursor:
            symbol = decode_cursor(cursor)["symbol"]
            items = [item for item in items if str(item.symbol) > symbol]
        has_more = len(items) > limit
        return items[:limit], has_more

    async def list_active_symbols(self) -> Sequence[str]:
        return [str(item.symbol) for item in self.instruments.values() if item.is_active]

    async def count(self) -> int:
        return len(self.instruments)


class InMemoryInstrumentCatalog:
    def __init__(self, repository: InMemoryInstrumentRepository) -> None:
        self._repository = repository

    async def get_by_symbol(self, symbol: str) -> InstrumentSummary | None:
        instrument = await self._repository.get_by_symbol(symbol)
        return _to_summary(instrument) if instrument is not None else None

    async def require_by_symbol(self, symbol: str) -> InstrumentSummary:
        summary = await self.get_by_symbol(symbol)
        if summary is None:
            raise NotFoundError("Instrument not found", details={"symbol": symbol.upper()})
        return summary


def _to_summary(instrument: Instrument) -> InstrumentSummary:
    return InstrumentSummary(
        id=instrument.id,
        symbol=str(instrument.symbol),
        name=instrument.name,
        asset_class=instrument.asset_class,
        currency=instrument.currency,
    )


class StubQuoteProvider:
    """Deterministic quote/history provider controlled by the test."""

    def __init__(
        self,
        *,
        prices: Mapping[str, Decimal] | None = None,
        history: Mapping[str, Sequence[PricePoint]] | None = None,
        fail: bool = False,
    ) -> None:
        self.prices: dict[str, Decimal] = dict(prices or {})
        self.history: dict[str, list[PricePoint]] = {
            symbol: list(points) for symbol, points in (history or {}).items()
        }
        self.fail = fail
        self.quote_calls: list[str] = []
        self.history_calls: list[tuple[str, date, date]] = []

    async def get_quote(self, symbol: str) -> QuoteView | None:
        self.quote_calls.append(symbol)
        if self.fail:
            raise ExternalServiceError("stub quote failure")
        price = self.prices.get(symbol.upper())
        if price is None:
            return None
        return QuoteView(
            symbol=symbol.upper(),
            price=Money(price, _currency_for(symbol)),
            as_of=datetime(2026, 6, 1, 18, 0, tzinfo=UTC),
            source="stub",
            change_percent=Decimal("0.50"),
        )

    async def get_quotes(self, symbols: Sequence[str]) -> Mapping[str, QuoteView]:
        if self.fail:
            raise ExternalServiceError("stub quote failure")
        quotes: dict[str, QuoteView] = {}
        for symbol in symbols:
            quote = await self.get_quote(symbol)
            if quote is not None:
                quotes[quote.symbol] = quote
        return quotes

    async def get_history(self, symbol: str, *, start: date, end: date) -> Sequence[PricePoint]:
        self.history_calls.append((symbol, start, end))
        if self.fail:
            raise ExternalServiceError("stub history failure")
        points = self.history.get(symbol.upper())
        if points is None:
            price = self.prices.get(symbol.upper())
            if price is None:
                return []
            currency = _currency_for(symbol)
            return [
                PricePoint(date=start + timedelta(days=offset), close=Money(price, currency))
                for offset in range((end - start).days + 1)
            ]
        return [point for point in points if start <= point.date <= end]


class StubMacroProvider:
    """Deterministic macro provider controlled by the test."""

    def __init__(
        self,
        *,
        series: Mapping[MacroSeriesCode, Sequence[IndexPointView]] | None = None,
        failing: set[MacroSeriesCode] | None = None,
    ) -> None:
        self.series: dict[MacroSeriesCode, list[IndexPointView]] = {
            code: list(points) for code, points in (series or {}).items()
        }
        self.failing = set(failing or ())
        self.series_calls: list[tuple[MacroSeriesCode, date, date]] = []
        self.latest_calls: list[MacroSeriesCode] = []

    async def get_series(
        self, code: MacroSeriesCode, *, start: date, end: date
    ) -> Sequence[IndexPointView]:
        self.series_calls.append((code, start, end))
        if code in self.failing:
            raise ExternalServiceError("stub macro failure")
        return [point for point in self.series.get(code, []) if start <= point.date <= end]

    async def latest(self, code: MacroSeriesCode) -> IndexPointView | None:
        self.latest_calls.append(code)
        if code in self.failing:
            raise ExternalServiceError("stub macro failure")
        points = self.series.get(code, [])
        return points[-1] if points else None


def _currency_for(symbol: str) -> Currency:
    return Currency.of("USD") if symbol.upper() in {"BTC", "ETH", "SOL"} else Currency.of("BRL")


class FastHasher:
    """Deterministic, instant hasher — never use outside tests."""

    def verify(self, password: PlainPassword, password_hash: str) -> bool:
        return self.hash(password) == password_hash

    def hash(self, password: PlainPassword) -> str:
        return "sha256$" + hashlib.sha256(password.value.encode()).hexdigest()

    def needs_rehash(self, password_hash: str) -> bool:
        return not password_hash.startswith("sha256$")

    def dummy_hash(self) -> str:
        return "sha256$" + "0" * 64


class FixedTokenService:
    """Deterministic tokens: ``access-<n>`` / ``refresh-<n>``."""

    def __init__(
        self,
        *,
        access_ttl: timedelta = timedelta(minutes=15),
        refresh_ttl: timedelta = timedelta(days=14),
    ) -> None:
        self._access_ttl = access_ttl
        self._refresh_ttl = refresh_ttl
        self._counter = 0

    def _next(self) -> int:
        self._counter += 1
        return self._counter

    def create_access_token(self, *, user_id: UUID, role: Role, now: datetime) -> IssuedToken:
        return IssuedToken(
            token=f"access-{self._next()}",
            expires_at=now + self._access_ttl,
            ttl_seconds=int(self._access_ttl.total_seconds()),
        )

    def create_refresh_token(self, *, user_id: UUID, now: datetime) -> IssuedToken:
        return IssuedToken(
            token=f"refresh-{self._next()}",
            expires_at=now + self._refresh_ttl,
            ttl_seconds=int(self._refresh_ttl.total_seconds()),
        )

    def decode_access_token(self, token: str, *, now: datetime) -> AccessTokenClaims:
        from basis.kernel.domain.errors import AuthenticationError

        raise AuthenticationError(
            "FixedTokenService cannot decode tokens", details={"token": token}
        )


class NullEventPublisher:
    def __init__(self) -> None:
        self.published: list[object] = []

    async def publish(self, events: Sequence[object]) -> None:
        self.published.extend(events)


class NoopUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def __aenter__(self) -> NoopUnitOfWork:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


__all__ = [
    "FastHasher",
    "FixedTokenService",
    "InMemoryClientDirectory",
    "InMemoryClientRepository",
    "InMemoryInstrumentCatalog",
    "InMemoryInstrumentRepository",
    "InMemoryRefreshTokenRepository",
    "InMemoryUserRepository",
    "NoopUnitOfWork",
    "NullEventPublisher",
    "StubMacroProvider",
    "StubQuoteProvider",
]
