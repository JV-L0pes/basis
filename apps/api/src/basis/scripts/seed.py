"""Seed the database with the reference catalog and, optionally, demo data.

Usage::

    uv run python -m basis.scripts.seed            # instruments + bootstrap admin
    uv run python -m basis.scripts.seed --demo     # plus demo clients and portfolios
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import timedelta
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
from basis.modules.market_data.infrastructure.providers.seed import SEED_INSTRUMENTS
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

DEMO_CLIENTS = (
    ("Ana Souza", "ana.souza@basis.dev", "52998224725", (4, 4, 3, 4, 4)),
    ("Bruno Lima", "bruno.lima@basis.dev", "11144477735", (3, 2, 3, 3, 2)),
    ("Carla Dias", "carla.dias@basis.dev", "12345678909", (1, 1, 2, 1, 2)),
)

DEMO_TRANSACTIONS = (
    ("PETR4", TransactionKind.BUY, Decimal(200), Decimal("35.10"), Decimal("4.90")),
    ("VALE3", TransactionKind.BUY, Decimal(100), Decimal("58.20"), Decimal("4.90")),
    ("BOVA11", TransactionKind.BUY, Decimal(50), Decimal("124.30"), Decimal("4.90")),
    ("IGUATEMI11", TransactionKind.BUY, Decimal(30), Decimal("87.10"), Decimal("4.90")),
    ("BTC", TransactionKind.BUY, Decimal("0.01"), Decimal("598000.00"), Decimal("120.00")),
    ("PETR4", TransactionKind.DIVIDEND, Decimal(1), Decimal("215.00"), Decimal(0)),
)


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
    async with session_factory() as session:
        clients_repo = SqlAlchemyClientRepository(session)
        clients_directory = SqlAlchemyClientDirectory(session)
        instruments = SqlAlchemyInstrumentCatalog(session)
        portfolios = SqlAlchemyPortfolioRepository(session)
        uow = SqlAlchemyUnitOfWork(session)

        register_client = RegisterClient(
            clients=clients_repo, clock=clock, uow=uow, events=bus
        )
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
        set_targets = SetAllocationTargets(
            portfolios=portfolios, clock=clock, uow=uow, events=bus
        )

        for name, email, tax_id, answers in DEMO_CLIENTS:
            if await clients_repo.get_by_tax_id(TaxId(tax_id)) is not None:
                print(f"cliente já existe: {name}")
                continue
            view = await register_client.execute(
                RegisterClientCommand(
                    name=name,
                    email=email,
                    tax_id=tax_id,
                    notes="Cliente de demonstração",
                    suitability_answers=list(answers),
                )
            )
            portfolio = await open_portfolio.execute(
                OpenPortfolioCommand(
                    client_id=view.id, name=f"Carteira {name.split()[0]}", base_currency="BRL"
                )
            )
            await set_targets.execute(
                SetTargetsCommand(
                    portfolio_id=portfolio.id,
                    targets=[
                        ("equity", 5500),
                        ("real_estate", 1500),
                        ("etf", 2000),
                        ("crypto", 1000),
                    ],
                )
            )
            for symbol, kind, quantity, price, fees in DEMO_TRANSACTIONS:
                await record.execute(
                    RecordTransactionCommand(
                        portfolio_id=portfolio.id,
                        symbol=symbol,
                        kind=str(kind),
                        trade_date=clock.today() - timedelta(days=120),
                        quantity=quantity,
                        price=price,
                        fees=fees,
                    )
                )


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
