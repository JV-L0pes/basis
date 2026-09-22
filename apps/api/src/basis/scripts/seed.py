"""Seed the database with the reference catalog and, optionally, demo data.

Usage::

    uv run python -m basis.scripts.seed            # instruments + bootstrap admin
    uv run python -m basis.scripts.seed --demo     # plus demo clients and portfolios
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from basis.config import Settings, get_settings
from basis.kernel.domain.clock import Clock, SystemClock
from basis.kernel.infrastructure.db import (
    SqlAlchemyUnitOfWork,
    create_engine,
    create_session_factory,
)
from basis.kernel.infrastructure.events import InProcessEventBus
from basis.modules.clients.application.use_cases import (
    RegisterClient,
    RegisterClientCommand,
)
from basis.modules.clients.domain.value_objects import TaxId
from basis.modules.clients.infrastructure.repository import (
    SqlAlchemyClientDirectory,
    SqlAlchemyClientRepository,
)
from basis.modules.identity.application.sessions import SessionIssuer
from basis.modules.identity.application.use_cases import RegisterUser, RegisterUserCommand
from basis.modules.identity.domain.value_objects import Email, PasswordPolicy
from basis.modules.identity.infrastructure.hashing import Argon2idHasher
from basis.modules.identity.infrastructure.repository import (
    SqlAlchemyRefreshTokenRepository,
    SqlAlchemyUserRepository,
)
from basis.modules.identity.infrastructure.tokens import JwtTokenService
from basis.modules.market_data.application.use_cases import SyncInstrumentCatalog
from basis.modules.market_data.infrastructure.providers.seed import (
    SEED_INSTRUMENTS,
    SeedQuoteProvider,
)
from basis.modules.market_data.infrastructure.repository import (
    SqlAlchemyInstrumentCatalog,
    SqlAlchemyInstrumentRepository,
)
from basis.modules.portfolio.application.use_cases import (
    OpenPortfolio,
    OpenPortfolioCommand,
    RecordTransaction,
    RecordTransactionCommand,
    SetAllocationTargets,
    SetTargetsCommand,
)
from basis.modules.portfolio.domain.value_objects import TransactionKind
from basis.modules.portfolio.infrastructure.repository import SqlAlchemyPortfolioRepository

DEMO_MONTHS = 12
BUY_DAY = 5
DIVIDEND_DAY = 15
DIVIDEND_YIELD = Decimal("0.007")
SELL_FRACTION = Decimal("0.2")
LOT_SIZE = Decimal("0.000001")


@dataclass(frozen=True, slots=True)
class DemoClient:
    """A client with a strategy: how the monthly contribution is allocated."""

    name: str
    email: str
    tax_id: str
    answers: tuple[int, ...]
    portfolio_name: str
    holdings: tuple[tuple[str, Decimal], ...]
    targets: tuple[tuple[str, int], ...]
    sells: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TransactionSpec:
    symbol: str
    kind: TransactionKind
    day: date
    quantity: Decimal
    price: Decimal
    fees: Decimal


MONTHLY_CONTRIBUTION = Decimal("2500.00")

DEMO_CLIENTS: tuple[DemoClient, ...] = (
    DemoClient(
        name="Ana Souza",
        email="ana.souza@basis.dev",
        tax_id="52998224725",
        answers=(4, 4, 3, 4, 4),
        portfolio_name="Carteira Ana · Arrojada",
        holdings=(
            ("PETR4", Decimal("0.30")),
            ("VALE3", Decimal("0.25")),
            ("BOVA11", Decimal("0.20")),
            ("BTC", Decimal("0.25")),
        ),
        targets=(("equity", 5500), ("etf", 2000), ("crypto", 2500)),
        sells=("VALE3",),
    ),
    DemoClient(
        name="Bruno Lima",
        email="bruno.lima@basis.dev",
        tax_id="11144477735",
        answers=(3, 2, 3, 3, 2),
        portfolio_name="Carteira Bruno · Moderada",
        holdings=(
            ("ITUB4", Decimal("0.30")),
            ("BBDC4", Decimal("0.20")),
            ("HGLG11", Decimal("0.30")),
            ("BOVA11", Decimal("0.20")),
        ),
        targets=(("equity", 5000), ("real_estate", 3000), ("etf", 2000)),
        sells=("ITUB4",),
    ),
    DemoClient(
        name="Carla Dias",
        email="carla.dias@basis.dev",
        tax_id="12345678909",
        answers=(1, 1, 2, 1, 2),
        portfolio_name="Carteira Carla · Conservadora",
        holdings=(
            ("TESOURO2029", Decimal("0.50")),
            ("CDB2027", Decimal("0.35")),
            ("IGUATEMI11", Decimal("0.15")),
        ),
        targets=(("fixed_income", 8500), ("real_estate", 1500)),
    ),
)

STAMP_DUTY = Decimal("0.0005")
MIN_FEE = Decimal("4.90")
CRYPTO_FEE = Decimal("0.001")
FEE_FREE = frozenset({"TESOURO2029", "CDB2027"})


def _month_day(today: date, months_ago: int, day: int) -> date:
    """Deterministic date ``months_ago`` months before ``today`` (clamped to day 28)."""
    month_index = today.month - 1 - months_ago
    year = today.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, min(day, 28))


def _fee_for(symbol: str, amount: Decimal) -> Decimal:
    if symbol in FEE_FREE:
        return Decimal(0)
    rate = CRYPTO_FEE if symbol in {"BTC", "ETH", "SOL"} else STAMP_DUTY
    return max((amount * rate).quantize(Decimal("0.01")), MIN_FEE)


async def _load_history(
    client: DemoClient, provider: SeedQuoteProvider, start: date, end: date
) -> dict[str, dict[date, Decimal]]:
    history: dict[str, dict[date, Decimal]] = {}
    for symbol, _ in client.holdings:
        points = await provider.get_history(symbol, start=start, end=end)
        history[symbol] = {point.date: point.close.amount for point in points}
    return history


def _price_on(history: dict[str, dict[date, Decimal]], symbol: str, day: date) -> Decimal | None:
    series = history.get(symbol, {})
    if day in series:
        return series[day]
    earlier = [moment for moment in series if moment <= day]
    return series[max(earlier)] if earlier else None


def _buys_for_month(
    client: DemoClient,
    history: dict[str, dict[date, Decimal]],
    today: date,
    months_ago: int,
    quantities: dict[str, Decimal],
) -> list[TransactionSpec]:
    buy_day = _month_day(today, months_ago, BUY_DAY)
    if buy_day > today:
        return []
    specs: list[TransactionSpec] = []
    for symbol, weight in client.holdings:
        price = _price_on(history, symbol, buy_day)
        if price is None or price <= 0:
            continue
        amount = (MONTHLY_CONTRIBUTION * weight).quantize(Decimal("0.01"))
        quantity = (amount / price).quantize(LOT_SIZE)
        if quantity <= 0:
            continue
        specs.append(
            TransactionSpec(
                symbol=symbol,
                kind=TransactionKind.BUY,
                day=buy_day,
                quantity=quantity,
                price=price,
                fees=_fee_for(symbol, amount),
            )
        )
        quantities[symbol] = quantities.get(symbol, Decimal(0)) + quantity
    return specs


def _dividends_for_month(
    client: DemoClient,
    history: dict[str, dict[date, Decimal]],
    today: date,
    months_ago: int,
    quantities: dict[str, Decimal],
) -> list[TransactionSpec]:
    dividend_day = _month_day(today, months_ago, DIVIDEND_DAY)
    if months_ago % 3 != 0 or dividend_day > today:
        return []
    specs: list[TransactionSpec] = []
    for symbol, _ in client.holdings:
        held = quantities.get(symbol, Decimal(0))
        price = _price_on(history, symbol, dividend_day) if held > 0 else None
        if price is None:
            continue
        cash = (held * price * DIVIDEND_YIELD).quantize(Decimal("0.01"))
        if cash <= 0:
            continue
        specs.append(
            TransactionSpec(
                symbol=symbol,
                kind=TransactionKind.DIVIDEND,
                day=dividend_day,
                quantity=Decimal(1),
                price=cash,
                fees=Decimal(0),
            )
        )
    return specs


def _sells_for_month(
    client: DemoClient,
    history: dict[str, dict[date, Decimal]],
    today: date,
    months_ago: int,
    quantities: dict[str, Decimal],
) -> list[TransactionSpec]:
    if months_ago != DEMO_MONTHS // 2:
        return []
    sell_day = _month_day(today, months_ago, 20)
    if sell_day > today:
        return []
    specs: list[TransactionSpec] = []
    for symbol in client.sells:
        held = quantities.get(symbol, Decimal(0))
        price = _price_on(history, symbol, sell_day) if held > 0 else None
        if price is None:
            continue
        quantity = (held * SELL_FRACTION).quantize(LOT_SIZE)
        if quantity <= 0:
            continue
        specs.append(
            TransactionSpec(
                symbol=symbol,
                kind=TransactionKind.SELL,
                day=sell_day,
                quantity=quantity,
                price=price,
                fees=_fee_for(symbol, quantity * price),
            )
        )
        quantities[symbol] = held - quantity
    return specs


async def _build_plan(
    client: DemoClient, provider: SeedQuoteProvider, *, today: date
) -> list[TransactionSpec]:
    """Replay a strategy over the last year using the same prices the API serves."""
    first_month = _month_day(today, DEMO_MONTHS - 1, BUY_DAY)
    history = await _load_history(client, provider, first_month, today)

    plan: list[TransactionSpec] = []
    quantities: dict[str, Decimal] = {}
    for months_ago in range(DEMO_MONTHS - 1, -1, -1):
        plan.extend(_buys_for_month(client, history, today, months_ago, quantities))
        plan.extend(_dividends_for_month(client, history, today, months_ago, quantities))
        plan.extend(_sells_for_month(client, history, today, months_ago, quantities))
    return sorted(plan, key=lambda spec: spec.day)


async def seed_instruments(
    session_factory: async_sessionmaker[AsyncSession],
    clock: Clock,
    bus: InProcessEventBus,
) -> int:
    async with session_factory() as session:
        use_case = SyncInstrumentCatalog(
            instruments=SqlAlchemyInstrumentRepository(session),
            clock=clock,
            uow=SqlAlchemyUnitOfWork(session),
            events=bus,
        )
        created = await use_case.execute(SEED_INSTRUMENTS)
        await session.commit()
        return created


async def seed_admin(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    clock: Clock,
    bus: InProcessEventBus,
) -> str | None:
    email = settings.auth.bootstrap_admin_email
    password = settings.auth.bootstrap_admin_password
    if not email or password is None:
        return None

    async with session_factory() as session:
        users = SqlAlchemyUserRepository(session)
        if await users.get_by_email(Email(email)) is not None:
            return None
        hasher = Argon2idHasher(
            time_cost=settings.auth.argon2_time_cost,
            memory_cost_kib=settings.auth.argon2_memory_cost_kib,
            parallelism=settings.auth.argon2_parallelism,
        )
        tokens = JwtTokenService(
            secret_key=settings.secret_key.get_secret_value(),
            algorithm=settings.auth.algorithm,
            access_ttl=timedelta(minutes=settings.auth.access_token_ttl_minutes),
            refresh_ttl=timedelta(days=settings.auth.refresh_token_ttl_days),
        )
        use_case = RegisterUser(
            users=users,
            hasher=hasher,
            policy=PasswordPolicy(),
            sessions=SessionIssuer(
                tokens=tokens,
                refresh_tokens=SqlAlchemyRefreshTokenRepository(session),
                clock=clock,
            ),
            clock=clock,
            uow=SqlAlchemyUnitOfWork(session),
            events=bus,
        )
        result = await use_case.execute(
            RegisterUserCommand(
                email=email,
                password=password.get_secret_value(),
                display_name="Basis Admin",
            )
        )
        return str(result.user.email)


async def seed_demo(
    session_factory: async_sessionmaker[AsyncSession],
    clock: Clock,
    bus: InProcessEventBus,
) -> None:
    provider = SeedQuoteProvider(clock)
    today = clock.today()

    async with session_factory() as session:
        clients_repo = SqlAlchemyClientRepository(session)
        clients_directory = SqlAlchemyClientDirectory(session)
        instruments = SqlAlchemyInstrumentCatalog(session)
        portfolios = SqlAlchemyPortfolioRepository(session)
        uow = SqlAlchemyUnitOfWork(session)

        register_client = RegisterClient(clients=clients_repo, clock=clock, uow=uow, events=bus)
        open_portfolio = OpenPortfolio(
            portfolios=portfolios,
            clients=clients_directory,
            clock=clock,
            uow=uow,
            events=bus,
        )
        record = RecordTransaction(
            portfolios=portfolios,
            instruments=instruments,
            clock=clock,
            uow=uow,
            events=bus,
        )
        set_targets = SetAllocationTargets(portfolios=portfolios, clock=clock, uow=uow, events=bus)

        for client in DEMO_CLIENTS:
            if await clients_repo.get_by_tax_id(TaxId(client.tax_id)) is not None:
                print(f"já existia: {client.name}")
                continue
            view = await register_client.execute(
                RegisterClientCommand(
                    name=client.name,
                    email=client.email,
                    tax_id=client.tax_id,
                    notes="Cliente de demonstração",
                    suitability_answers=list(client.answers),
                )
            )
            portfolio = await open_portfolio.execute(
                OpenPortfolioCommand(
                    client_id=view.id, name=client.portfolio_name, base_currency="BRL"
                )
            )
            await set_targets.execute(
                SetTargetsCommand(
                    portfolio_id=portfolio.id,
                    targets=[(asset_class, bps) for asset_class, bps in client.targets],
                )
            )
            plan = await _build_plan(client, provider, today=today)
            for spec in plan:
                await record.execute(
                    RecordTransactionCommand(
                        portfolio_id=portfolio.id,
                        symbol=spec.symbol,
                        kind=str(spec.kind),
                        trade_date=spec.day,
                        quantity=spec.quantity,
                        price=spec.price,
                        fees=spec.fees,
                    )
                )
            print(f"{client.name}: {len(plan)} lançamentos")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the Basis database")
    parser.add_argument("--demo", action="store_true", help="also create demo clients")
    arguments = parser.parse_args()

    settings = get_settings()
    clock = SystemClock()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    bus = InProcessEventBus()

    try:
        created = await seed_instruments(session_factory, clock, bus)
        print(f"instrumentos criados: {created}")
        admin = await seed_admin(session_factory, settings, clock, bus)
        print(f"admin: {admin or 'já existia'}")
        if arguments.demo:
            await seed_demo(session_factory, clock, bus)
            print("dados de demonstração criados")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main(), loop_factory=asyncio.SelectorEventLoop)


__all__ = ["main", "seed_demo", "seed_instruments"]
