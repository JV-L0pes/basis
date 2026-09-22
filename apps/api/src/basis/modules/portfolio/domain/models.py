"""Portfolio domain models: transactions, positions, the Portfolio aggregate."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from basis.kernel.domain.clock import Clock
from basis.kernel.domain.currency import Currency
from basis.kernel.domain.entity import AggregateRoot, Entity
from basis.kernel.domain.errors import InvariantViolationError, ValidationError
from basis.kernel.domain.identifiers import new_id
from basis.kernel.domain.money import Money
from basis.modules.portfolio.domain.events import (
    AllocationTargetsSet,
    PortfolioArchived,
    PortfolioOpened,
    TransactionRecorded,
)
from basis.modules.portfolio.domain.value_objects import (
    AllocationTargets,
    InstrumentRef,
    PortfolioStatus,
    TransactionKind,
)

NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 80
NOTES_MAX_LENGTH = 280


@dataclass(eq=False, slots=True)
class Transaction(Entity[UUID]):
    """A movement in the portfolio ledger.

    ``gross_value`` is always ``quantity * price``. For income and expense kinds
    the convention is ``quantity = 1`` and ``price`` = cash amount, so the gross
    value is the cash flow itself.
    """

    instrument: InstrumentRef
    kind: TransactionKind
    trade_date: date
    quantity: Decimal
    price: Money
    fees: Money
    notes: str | None
    created_at: datetime

    @classmethod
    def record(
        cls,
        *,
        instrument: InstrumentRef,
        kind: TransactionKind,
        trade_date: date,
        quantity: Decimal,
        price: Money,
        fees: Money | None = None,
        notes: str | None = None,
        clock: Clock,
    ) -> Transaction:
        if quantity <= 0:
            raise ValidationError(
                "Transaction quantity must be positive", details={"quantity": str(quantity)}
            )
        if price.is_negative():
            raise ValidationError("Transaction price cannot be negative")
        if price.currency != instrument.currency:
            raise ValidationError(
                "Transaction price currency must match the instrument currency",
                details={"expected": instrument.currency.code, "actual": price.currency.code},
            )

        resolved_fees = fees or Money.zero(instrument.currency)
        if resolved_fees.is_negative():
            raise ValidationError("Transaction fees cannot be negative")
        if resolved_fees.currency != instrument.currency:
            raise ValidationError("Fees currency must match the instrument currency")

        return cls(
            id=new_id(),
            instrument=instrument,
            kind=kind,
            trade_date=trade_date,
            quantity=quantity,
            price=price,
            fees=resolved_fees,
            notes=_validate_notes(notes),
            created_at=clock.now(),
        )

    @property
    def gross_value(self) -> Money:
        return (self.price * self.quantity).quantize()

    @property
    def cash_flow(self) -> Money:
        """Net cash movement: negative when money leaves the investor's pocket."""
        if self.kind is TransactionKind.BUY:
            return -(self.gross_value + self.fees)
        if self.kind is TransactionKind.SELL:
            return self.gross_value - self.fees
        if self.kind.is_cash_income:
            return self.gross_value - self.fees
        return -(self.gross_value + self.fees)  # FEE


def _validate_notes(notes: str | None) -> str | None:
    if notes is None:
        return None
    normalized = notes.strip()
    if not normalized:
        return None
    if len(normalized) > NOTES_MAX_LENGTH:
        raise ValidationError(
            f"Notes must be at most {NOTES_MAX_LENGTH} characters",
            details={"length": len(normalized)},
        )
    return normalized


@dataclass(frozen=True, slots=True)
class Position:
    """The result of folding every transaction of one instrument.

    Positions are immutable: :meth:`apply` returns the next state, which keeps
    the ledger the single source of truth and makes the fold trivially testable.
    """

    instrument: InstrumentRef
    quantity: Decimal
    average_cost: Money
    realized_gain: Money
    income: Money
    costs: Money

    @classmethod
    def open(cls, instrument: InstrumentRef) -> Position:
        zero = Money.zero(instrument.currency)
        return cls(
            instrument=instrument,
            quantity=Decimal(0),
            average_cost=zero,
            realized_gain=zero,
            income=zero,
            costs=zero,
        )

    @property
    def cost_basis(self) -> Money:
        return (self.average_cost * self.quantity).quantize()

    @property
    def net_result(self) -> Money:
        """Realized gains plus income minus every fee paid."""
        return (self.realized_gain + self.income - self.costs).quantize()

    @property
    def is_open(self) -> bool:
        return self.quantity > 0

    def apply(self, transaction: Transaction) -> Position:
        """Return the position after applying ``transaction``."""
        if transaction.instrument.symbol != self.instrument.symbol:
            raise ValidationError(
                "Transaction does not belong to this position",
                details={
                    "expected": self.instrument.symbol,
                    "actual": transaction.instrument.symbol,
                },
            )

        kind = transaction.kind
        if kind is TransactionKind.BUY:
            total_cost = transaction.gross_value + transaction.fees
            new_quantity = self.quantity + transaction.quantity
            new_average = ((self.cost_basis + total_cost) / new_quantity).quantize()
            return replace(
                self,
                quantity=new_quantity,
                average_cost=new_average,
                costs=self.costs + transaction.fees,
            )

        if kind is TransactionKind.SELL:
            if transaction.quantity > self.quantity:
                raise InvariantViolationError(
                    "Cannot sell more than the position holds",
                    details={
                        "symbol": self.instrument.symbol,
                        "held": str(self.quantity),
                        "sold": str(transaction.quantity),
                    },
                )
            proceeds = transaction.gross_value - transaction.fees
            cost = (self.average_cost * transaction.quantity).quantize()
            new_quantity = self.quantity - transaction.quantity
            average = (
                self.average_cost if new_quantity > 0 else Money.zero(self.instrument.currency)
            )
            return replace(
                self,
                quantity=new_quantity,
                average_cost=average,
                realized_gain=self.realized_gain + (proceeds - cost),
                costs=self.costs + transaction.fees,
            )

        if kind.is_cash_income:
            net_income = transaction.gross_value - transaction.fees
            return replace(
                self,
                income=self.income + net_income,
                costs=self.costs + transaction.fees,
            )

        # FEE
        total_fee = transaction.gross_value + transaction.fees
        return replace(self, costs=self.costs + total_fee)


@dataclass(eq=False, slots=True)
class Portfolio(AggregateRoot[UUID]):
    """A client's set of positions, its ledger and its allocation targets."""

    client_id: UUID
    name: str
    base_currency: Currency
    status: PortfolioStatus
    targets: AllocationTargets
    transactions: tuple[Transaction, ...]
    created_at: datetime
    updated_at: datetime

    # -- factories --------------------------------------------------------
    @classmethod
    def open(
        cls,
        *,
        client_id: UUID,
        name: str,
        base_currency: Currency,
        clock: Clock,
    ) -> Portfolio:
        moment = clock.now()
        portfolio = cls(
            id=new_id(),
            client_id=client_id,
            name=_validate_name(name),
            base_currency=base_currency,
            status=PortfolioStatus.ACTIVE,
            targets=AllocationTargets.empty(),
            transactions=(),
            created_at=moment,
            updated_at=moment,
        )
        portfolio.record(
            PortfolioOpened(
                occurred_at=moment,
                portfolio_id=portfolio.id,
                client_id=client_id,
                portfolio_name=portfolio.name,
            )
        )
        return portfolio

    # -- commands ---------------------------------------------------------
    def rename(self, name: str, *, clock: Clock) -> None:
        self._ensure_active("renamed")
        self.name = _validate_name(name)
        self.updated_at = clock.now()

    def set_targets(self, targets: AllocationTargets, *, clock: Clock) -> None:
        self._ensure_active("re-targeted")
        moment = clock.now()
        self.targets = targets
        self.updated_at = moment
        self.record(
            AllocationTargetsSet(occurred_at=moment, portfolio_id=self.id, targets=len(targets))
        )

    def record_transaction(self, transaction: Transaction, *, clock: Clock) -> None:
        """Append a transaction after enforcing the aggregate invariants."""
        self._ensure_active("traded")
        if transaction.instrument.currency != self.base_currency:
            raise ValidationError(
                "Transaction currency must match the portfolio base currency",
                details={
                    "base_currency": self.base_currency.code,
                    "transaction_currency": transaction.instrument.currency.code,
                },
            )
        if transaction.trade_date > clock.today():
            raise ValidationError(
                "Transaction date cannot be in the future",
                details={"trade_date": transaction.trade_date.isoformat()},
            )

        # Dry-run the fold so impossible trades are rejected before persisting.
        self._position_for(transaction.instrument).apply(transaction)
        self.transactions = (*self.transactions, transaction)
        self.updated_at = clock.now()
        self.record(
            TransactionRecorded(
                occurred_at=self.updated_at,
                portfolio_id=self.id,
                transaction_id=transaction.id,
                kind=str(transaction.kind),
                symbol=transaction.instrument.symbol,
            )
        )

    def archive(self, *, clock: Clock) -> None:
        if self.status is PortfolioStatus.ARCHIVED:
            return
        moment = clock.now()
        self.status = PortfolioStatus.ARCHIVED
        self.updated_at = moment
        self.record(PortfolioArchived(occurred_at=moment, portfolio_id=self.id))

    # -- queries ----------------------------------------------------------
    @property
    def is_active(self) -> bool:
        return self.status is PortfolioStatus.ACTIVE

    def instruments(self) -> tuple[InstrumentRef, ...]:
        seen: dict[str, InstrumentRef] = {}
        for transaction in self.transactions:
            seen.setdefault(transaction.instrument.symbol, transaction.instrument)
        return tuple(seen[symbol] for symbol in sorted(seen))

    def positions(self) -> tuple[Position, ...]:
        """Fold the ledger into positions, one per traded instrument."""
        positions: dict[str, Position] = {}
        for transaction in self.transactions:
            symbol = transaction.instrument.symbol
            current = positions.get(symbol) or Position.open(transaction.instrument)
            positions[symbol] = current.apply(transaction)
        return tuple(positions[symbol] for symbol in sorted(positions))

    def transaction_count(self) -> int:
        return len(self.transactions)

    def _position_for(self, instrument: InstrumentRef) -> Position:
        """Return the current position, or an empty one for a new instrument."""
        for position in self.positions():
            if position.instrument.symbol == instrument.symbol:
                return position
        return Position.open(instrument)

    def _ensure_active(self, action: str) -> None:
        if self.status is PortfolioStatus.ARCHIVED:
            raise InvariantViolationError(f"archived portfolios cannot be {action}")


def _validate_name(name: str) -> str:
    normalized = " ".join(name.split())
    if not (NAME_MIN_LENGTH <= len(normalized) <= NAME_MAX_LENGTH):
        raise ValidationError(
            f"Portfolio name must be between {NAME_MIN_LENGTH} and {NAME_MAX_LENGTH} characters",
            details={"length": len(normalized)},
        )
    return normalized


__all__ = [
    "NAME_MAX_LENGTH",
    "NAME_MIN_LENGTH",
    "NOTES_MAX_LENGTH",
    "Portfolio",
    "Position",
    "Transaction",
]
