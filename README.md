# Basis

> Plataforma de gestão de investimentos para o mercado brasileiro — clientes, carteiras,
> extrato, posições, performance, risco e dados de mercado em um monolito modular com
> frontend próprio.

[![CI](https://github.com/JV-L0pes/basis/actions/workflows/ci.yml/badge.svg)](https://github.com/JV-L0pes/basis/actions/workflows/ci.yml)

**English:** [README.en.md](README.en.md) — Basis is an investment management platform for the Brazilian market: a DDD modular monolith (FastAPI + SQLAlchemy) with a React/Vite SPA built on the "Ink" design system, live market data with a deterministic fallback, and financial mathematics (TWR, XIRR, risk metrics, rebalancing) covered by 519 tests.

> Codename interno: `basis` (pacotes `@basis/*`, pacote Python `basis`, envs `BASIS_*`).

---

## O que é isto

O projeto nasceu como um case de processo seletivo (Fastify + Prisma + Next.js, catálogo de ativos *hardcoded*, nenhum teste) e foi reescrito como uma ferramenta de mercado de verdade. O diagnóstico e as decisões estão no [case study](docs/case-study.md).

- **Clientes**: CPF/CNPJ validados de verdade (dígitos verificadores), questionário de suitability que gera perfil de risco, busca, arquivamento reversível.
- **Carteiras**: extrato *append-only* de compras, vendas, proventos e taxas; posições derivadas por custo médio ponderado (nunca dessincronizadas do extrato); alocação alvo em basis points; valoração mark-to-market com P&L por posição.
- **Mercado**: catálogo com ISIN/MIC/CFI, cotações de **brapi.dev**, **Yahoo Finance** e **BCB SGS** com cache e fallback determinístico, séries macro (Selic, CDI, IPCA, USD/BRL) e histórico para gráficos.
- **Analytics**: TWR, XIRR, volatilidade anualizada, Sharpe (Selic como taxa livre de risco), beta vs. Ibovespa, drawdown máximo, VaR 95%, drift de alocação em bps e plano de rebalanceamento.
- **Identidade**: Argon2id, access token curto em memória, refresh opaco rotativo em cookie httpOnly com detecção de reuso, papéis admin/advisor/viewer.
- **Interface**: SPA em React 19 sobre o design system **Ink** (tipografia editorial, hairlines, zero sombra), tema claro/escuro, i18n PT/EN e gráficos em SVG próprio.

## Arquitetura

```
apps/api   FastAPI + SQLAlchemy 2 async (DDD modular: identity, clients, portfolio, market_data, analytics)
apps/web   React 19 + Vite + Tailwind v4 + TanStack Query/Router (Feature-Sliced Design)
packages/  ui (design system Ink) · contracts (OpenAPI 3.1 -> TypeScript)
docs/      ADRs, case study, catálogo de regras, runbook
```

Cada contexto tem `domain` / `application` / `infrastructure` / `presentation`, integra por contratos publicados e eventos, e **não** importa as tabelas ou entidades de outro contexto — regra verificada por 8 contratos de `import-linter` no CI. Detalhes em [ARCHITECTURE.md](ARCHITECTURE.md), decisões em [`docs/adr/`](docs/adr/), regras rastreáveis em [`docs/domain/catalogo.md`](docs/domain/catalogo.md) e operação em [`docs/runbook/operacao.md`](docs/runbook/operacao.md).

## Rodando localmente

Pré-requisitos: Docker, Node 22+, pnpm 9+, Python 3.13+ e [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env                              # ajuste BASIS_SECRET_KEY e a senha do admin
docker compose up -d db                           # Postgres 16 (+ basis_test)

uv sync --directory apps/api
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api python -m basis.scripts.seed --demo   # catálogo + admin + demo
uv run --directory apps/api python -m basis                       # API :8100 (/docs)

pnpm install
pnpm --filter @basis/web dev                                      # web :5174
```

Acesso local: `admin@basis.dev` com a senha definida em `BASIS_AUTH__BOOTSTRAP_ADMIN_PASSWORD` — ou **crie a sua própria conta na tela de acesso** (entrar/criar conta; o primeiro usuário vira admin, os seguintes entram como advisor). O seed `--demo` cria três clientes com estratégias diferentes e **12 meses de histórico** (aportes mensais, proventos trimestrais e uma venda parcial), então os gráficos e as métricas de performance têm o que mostrar.

> **Windows:** o psycopg async exige event loop `Selector`; use `python -m basis` (entrypoint que configura o loop). No Linux/Docker o `uvicorn` padrão funciona.
> **Portas:** os padrões são `8000` (API), `5173` (web) e `5432` (banco); o `.env` permite trocar (`BASIS_PORT`, `BASIS_DB_PORT`) quando houver conflito local.

### Tudo com Docker

```bash
docker compose --profile full up --build     # web em http://localhost:5173
```

## Qualidade

```bash
pnpm turbo run lint typecheck test build     # web + design system + contratos
pnpm check                                   # Biome (formatação e lint base)
pnpm lint:eslint                             # ESLint type-aware: a11y, hooks, ciclos, FSD
pnpm knip                                    # código e dependências mortas

uv run --directory apps/api ruff check .
uv run --directory apps/api mypy src tests
uv run --directory apps/api lint-imports     # fronteiras entre bounded contexts
uv run --directory apps/api pytest           # 470 testes (domínio, integração, HTTP)
```

São **519 testes**: 470 na API, 25 no web (páginas com MSW, login, i18n) e 24 no design system. O CI roda tudo isso, aplica as migrações Alembic em um Postgres real, valida o contrato OpenAPI e ainda executa `gitleaks` e `pip-audit`.

## Dados de mercado

Com `BASIS_MARKET_DATA__ALLOW_LIVE_PROVIDERS=true` (padrão), a resposta sai **imediatamente** com a série determinística e o provedor real atualiza o cache em background — a tela nunca espera por uma API externa. O painel mostra `ao vivo` quando a origem não é o seed. Com `false`, tudo funciona offline com preços estáveis (útil para testes e demonstrações).

## Estrutura de pastas

```
apps/api/src/basis/
  kernel/           shared kernel (Money, Currency, Entity, eventos, DB, HTTP)
  modules/
    identity/       usuários, sessões, papéis
    clients/        investidores, CPF/CNPJ, suitability
    portfolio/      carteiras, extrato, posições, alvos
    market_data/    instrumentos, cotações, macro, provedores
    analytics/      performance, risco, alocação, rebalanceamento
apps/web/src/       app · pages · widgets · features · entities · shared   (FSD)
packages/ui/        design system Ink + primitivos + gráficos
packages/contracts/ openapi.json + tipos gerados
```

## Roadmap

- **Próximos passos**: multi-moeda com PTAX, renda fixa com curva/PU e day count BUS/252, snapshots materializados de posição, Open Finance/CVM e observabilidade (OpenTelemetry).
- **Fora de escopo por enquanto**: negociação/ordens, multi-tenant com times, notificações e exportação de relatórios.

## Licença

MIT — veja [LICENSE](LICENSE). Autor: João Victor Lopes ([JV-L0pes](https://github.com/JV-L0pes)).
