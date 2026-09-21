# Basis

Plataforma de gestão de investimentos para o mercado financeiro brasileiro — clientes,
carteiras, posições, performance, risco e dados de mercado em um único monolito
modular com frontend próprio.

> **Status:** walking skeleton completo. Backend com 439 testes (domínio,
> integração e API), frontend com 35 testes (design system, i18n, formulários) e
> 8 contratos de arquitetura verificados em CI.

---

## Visão geral

| Área | O que existe hoje |
| --- | --- |
| **Identidade** | Registro, login com Argon2id, JWT de acesso + refresh rotativo com detecção de reuso, papéis (admin/advisor/viewer), change-password com revogação de sessões |
| **Clientes** | Cadastro com validação real de CPF/CNPJ (dígitos verificadores), questionário de suitability (5–10 respostas → perfil conservador/moderado/arrojado), busca, filtro por situação, arquivamento reversível |
| **Carteiras** | Abertura por cliente, moeda base, alocação alvo em basis points (soma exata de 100%), extrato de compras/vendas/dividendos/juros/taxas, posições derivadas do extrato por custo médio ponderado, valuação mark-to-market |
| **Mercado** | Catálogo de instrumentos (ISIN com Luhn, MIC ISO 10383, CFI ISO 10962), cotações com cache TTL e fallback determinístico, séries macro do BCB (Selic, CDI, IPCA, USD/BRL), candles/histórico |
| **Analytics** | TWR, XIRR, volatilidade anualizada, Sharpe, beta, drawdown máximo, VaR 95%, alocação atual vs. alvo, drift em basis points e plano de rebalanceamento |
| **Design** | Sistema "Ink" (tipografia editorial, hairlines, zero sombras) em `@basis/ui`, tema claro/escuro, i18n PT/EN com paridade tipada |
| **Qualidade** | Ruff (com bandit/S/B/TRY) + mypy strict + import-linter (fronteiras entre contextos) no Python; Biome (formatação/lint) + ESLint type-aware (sonarjs, jsx-a11y, react-hooks, ciclos de import, regras de FSD por camada) + Knip (código morto) no TypeScript |

---

## Arquitetura

Monorepo poliglota, monolito modular no backend e Feature-Sliced Design no
frontend. O detalhamento está em [`ARCHITECTURE.md`](./ARCHITECTURE.md).

```
investment-management-platform/
├─ apps/
│  ├─ api/                          # FastAPI — monolito modular (DDD)
│  │  └─ src/basis/
│  │     ├─ kernel/                 # shared kernel: Money, Currency, Entity, eventos, DB, HTTP
│  │     └─ modules/                # bounded contexts
│  │        ├─ identity/            # autenticação, usuários, sessões
│  │        ├─ clients/              # investidores, CPF/CNPJ, suitability
│  │        ├─ portfolio/            # carteiras, extrato, posições, valuação
│  │        ├─ market_data/          # instrumentos, cotações, macro, providers
│  │        └─ analytics/            # performance, risco, alocação, rebalanceamento
│  └─ web/                          # Vite + React 19 — FSD
│     └─ src/{app,pages,widgets,features,entities,shared}
├─ packages/
│  ├─ ui/                           # design system Ink + primitivos shadcn-style + charts
│  └─ contracts/                    # OpenAPI 3.1 → tipos TypeScript
├─ ops/                             # init do Postgres
└─ .github/workflows/ci.yml
```

Cada contexto tem quatro camadas — `domain`, `application`, `infrastructure`,
`presentation` — com dependências apontando para dentro. O `import-linter`
**quebra o build** se um domínio importar outro contexto, SQLAlchemy, FastAPI ou
Pydantic.

---

## Stack

| Camada | Escolhas |
| --- | --- |
| Backend | Python 3.14, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 16, Pydantic v2, structlog, PyJWT, Argon2id, httpx + tenacity |
| Frontend | Vite 6, React 19, TypeScript strict, TanStack Query + Router, openapi-fetch, react-hook-form + zod, Tailwind v4, Radix primitives, lightweight-charts |
| Infra | Docker Compose (Postgres + api + web/nginx), GitHub Actions, Dependabot, pre-commit + gitleaks |

---

## Como rodar

Pré-requisitos: Docker, Node 22+, pnpm 9+, Python 3.13+ e [uv](https://docs.astral.sh/uv/).

```bash
# 1. Configuração
cp .env.example .env          # ajuste BASIS_SECRET_KEY e credenciais

# 2. Banco
docker compose up -d db

# 3. Backend
uv sync --directory apps/api
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api python -m basis.scripts.seed --demo
uv run --directory apps/api uvicorn basis.main:app --reload --port 8000
#   API:   http://localhost:8000/docs
#   Health: http://localhost:8000/api/v1/health

# 4. Frontend
pnpm install
pnpm --filter @basis/web dev   # http://localhost:5173
```

Usuário criado pelo seed: `admin@basis.dev` (senha em `BASIS_AUTH__BOOTSTRAP_ADMIN_PASSWORD`).
Os dados de demonstração criam três clientes, três carteiras e lançamentos.

> **Windows:** psycopg async exige event loop `Selector`. Use
> `uv run --directory apps/api python -m basis` (entrypoint que configura o loop)
> ou `pnpm --filter @basis/web dev` normalmente. No Linux/Docker o uvicorn padrão funciona.

### Tudo com Docker

```bash
docker compose --profile full up --build   # web em http://localhost:5173
```

---

## Comandos

| Comando | O que faz |
| --- | --- |
| `pnpm dev` | Frontend + tasks do Turborepo em modo dev |
| `pnpm build` / `pnpm typecheck` / `pnpm test` / `pnpm lint` | Pipeline completo do frontend |
| `pnpm check` | Biome (format + lint) em todo o monorepo |
| `pnpm lint:eslint` | ESLint type-aware (a11y, segurança, FSD, testes) |
| `pnpm knip` | Detecção de código e dependências mortas |
| `pnpm py:lint` / `pnpm py:typecheck` / `pnpm py:test` | Ruff, mypy e pytest do backend |
| `pnpm db:migrate` / `pnpm db:seed` | Alembic e seed (use `-- --demo` para dados de exemplo) |
| `pnpm openapi:export` / `pnpm openapi:check` | Exporta/valida o contrato consumido pelo frontend |
| `pnpm contracts:generate` | Gera os tipos TypeScript a partir do OpenAPI |

---

## Padrões e convenções

- **Dinheiro nunca é float.** `Decimal` no Python (`NUMERIC(28,10)` no Postgres) e
  string no JSON; o frontend faz arredondamento apenas para exibição.
- **Arredondamento** bancário (half-even) na menor unidade da moeda; divisões de
  custo médio são limitadas a 12 casas no kernel.
- **Datas**: ISO 8601 / RFC 3339 em UTC; `Clock` injetado — o domínio nunca chama
  `datetime.now`.
- **Identificadores**: UUIDv7 (ordenados por tempo) para chaves primárias.
- **Identificação de ativos**: ISIN (ISO 6166, com Luhn), MIC (ISO 10383), CFI (ISO 10962).
- **Erros HTTP**: RFC 9457 (`application/problem+json`) com `code` estável e
  `X-Request-ID` em toda resposta.
- **Paginação**: cursor opaco (keyset) para clientes, carteiras e instrumentos.
- **Eventos de domínio** publicados após o commit via barramento in-process.
- **API**: OpenAPI 3.1 gerado pelo FastAPI e versionado em `packages/contracts`.

Convenções de código e fluxo de trabalho para agentes e pessoas estão em
[`AGENTS.md`](./AGENTS.md). Decisões de arquitetura e padrões do mercado
financeiro (TWR/XIRR, day count, alocação) estão em [`ARCHITECTURE.md`](./ARCHITECTURE.md).

---

## Licença

MIT.
