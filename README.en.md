# Basis

> An investment management platform for the Brazilian market — clients, portfolios,
> ledger, positions, performance, risk and market data in a modular monolith with its
> own frontend.

[![CI](https://github.com/JV-L0pes/basis/actions/workflows/ci.yml/badge.svg)](https://github.com/JV-L0pes/basis/actions/workflows/ci.yml)

**Português:** [README.md](README.md) — Basis é uma plataforma de gestão de investimentos para o mercado brasileiro: monolito modular com DDD (FastAPI + SQLAlchemy), SPA em React/Vite com o design system "Ink", dados de mercado ao vivo com fallback determinístico e matemática financeira (TWR, XIRR, risco, rebalanceamento) coberta por 519 testes.

> Internal codename: `basis` (packages `@basis/*`, Python package `basis`, envs `BASIS_*`).

---

## What this is

The project started as a hiring-case CRUD (Fastify + Prisma + Next.js, hardcoded asset catalog, zero tests) and was rewritten as a real market tool. The diagnosis and the decisions live in the [case study](docs/case-study.md) (Portuguese).

- **Clients**: real CPF/CNPJ validation (check digits), a suitability questionnaire that derives a risk profile, search and reversible archiving.
- **Portfolios**: append-only ledger of buys, sells, income and fees; positions derived by weighted-average cost (never out of sync with the ledger); target allocation in basis points; mark-to-market valuation with per-position P&L.
- **Markets**: instrument catalog with ISIN/MIC/CFI, quotes from **brapi.dev**, **Yahoo Finance** and **BCB SGS** with cache and a deterministic fallback, macro series (Selic, CDI, IPCA, USD/BRL) and price history for charts.
- **Analytics**: TWR, XIRR, annualised volatility, Sharpe (Selic as the risk-free rate), beta vs. Ibovespa, max drawdown, historical VaR 95%, allocation drift in bps and a rebalancing plan.
- **Identity**: Argon2id, short-lived access token in memory, opaque rotating refresh token in an httpOnly cookie with reuse detection, admin/advisor/viewer roles.
- **Interface**: React 19 SPA on the **Ink** design system (editorial typography, hairlines, no shadows), light/dark theme, PT/EN i18n and hand-rolled SVG charts.

## Architecture

```
apps/api   FastAPI + SQLAlchemy 2 async (DDD modules: identity, clients, portfolio, market_data, analytics)
apps/web   React 19 + Vite + Tailwind v4 + TanStack Query/Router (Feature-Sliced Design)
packages/  ui (Ink design system) · contracts (OpenAPI 3.1 -> TypeScript)
docs/      ADRs, case study, rule catalog, runbook
```

Every context has `domain` / `application` / `infrastructure` / `presentation`, integrates through published contracts and domain events, and never imports another context's tables or entities — enforced by 8 `import-linter` contracts in CI.

## Running locally

Requirements: Docker, Node 22+, pnpm 9+, Python 3.13+ and [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env                              # set BASIS_SECRET_KEY and the admin password
docker compose up -d db                           # Postgres 16 (+ basis_test)

uv sync --directory apps/api
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api python -m basis.scripts.seed --demo
uv run --directory apps/api python -m basis                       # API on :8100 (/docs)

pnpm install
pnpm --filter @basis/web dev                                      # web on :5174
```

Local credentials: `admin@basis.dev` with the password from `BASIS_AUTH__BOOTSTRAP_ADMIN_PASSWORD` — or **create your own account on the sign-in screen** (first user becomes an admin, the following ones advisors). The `--demo` seed creates three clients with different strategies and 12 months of history, so charts and performance metrics have real data to show.

> **Windows:** psycopg async needs a `Selector` event loop; use `python -m basis`. On Linux/Docker plain `uvicorn` is fine.
> **Ports:** defaults are `8000` (API), `5173` (web) and `5432` (database); the `.env` lets you move them when a local conflict exists.

### Everything in Docker

```bash
docker compose --profile full up --build     # web on http://localhost:5173
```

## Quality

```bash
pnpm turbo run lint typecheck test build     # web + design system + contracts
pnpm check                                   # Biome (formatting and base lint)
pnpm lint:eslint                             # type-aware ESLint: a11y, hooks, cycles, FSD
pnpm knip                                    # dead code and unused dependencies

uv run --directory apps/api ruff check .
uv run --directory apps/api mypy src tests
uv run --directory apps/api lint-imports     # bounded context boundaries
uv run --directory apps/api pytest           # 470 tests (domain, integration, HTTP)
```

**519 tests** in total: 470 on the API, 25 on the web (MSW page tests, login, i18n) and 24 in the design system. CI runs all of it, applies Alembic migrations against a real Postgres, validates the OpenAPI contract and runs `gitleaks`/`pip-audit`.

## Market data

With `BASIS_MARKET_DATA__ALLOW_LIVE_PROVIDERS=true` (default) the response is served **immediately** from the deterministic series while the real provider refreshes the cache in the background — the screen never waits on an external API. The dashboard shows `live` when the source is not the seed. Set it to `false` to run fully offline with stable prices.

## Roadmap

- **Next**: multi-currency with PTAX, fixed income with curve/dirty price and BUS/252 day count, materialised position snapshots, Open Finance/CVM ingestion and observability (OpenTelemetry).
- **Out of scope for now**: order execution, multi-tenant teams, notifications and report exports.

## License

MIT — see [LICENSE](LICENSE). Author: João Victor Lopes ([JV-L0pes](https://github.com/JV-L0pes)).
