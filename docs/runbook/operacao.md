# Runbook de operação — Basis

## Ambientes

| Ambiente | Web | API | Banco |
|---|---|---|---|
| Local | `pnpm --filter @basis/web dev` (`:5174`) | `uv run --directory apps/api python -m basis` (`:8100`) | Postgres 16 via Docker Compose (`:55432` nesta máquina) |
| Docker (tudo junto) | `docker compose --profile full up --build` (`:5173`) | mesma stack, porta `8000` | `basis_db` (`:5432` padrão) |
| CI | build de produção (`pnpm turbo build`) | pytest contra Postgres de serviço | `postgres:16-alpine` |

> **Portas:** os padrões do projeto são `8000` (API), `5173` (web) e `5432` (banco). Nesta máquina há outros projetos ocupando `8000`, `5173` e `5432`, então o `.env` local usa `BASIS_PORT=8100`, `VITE_API_URL=http://localhost:8100`, `BASIS_DB_PORT=55432` e o Vite sobe em `5174`.

## Variáveis de ambiente da API

Todas usam o prefixo `BASIS_`; settings aninhados usam `__` (ex.: `BASIS_AUTH__ACCESS_TOKEN_TTL_MINUTES`).

| Variável | Padrão | Notas |
|---|---|---|
| `BASIS_ENVIRONMENT` | `local` | `local`/`test`/`staging`/`production`; em produção os cookies exigem HTTPS |
| `BASIS_SECRET_KEY` | — | **obrigatória**; ≥32 bytes aleatórios (assina os JWT) |
| `BASIS_DATABASE_URL` | `postgresql+psycopg://basis:basis@localhost:5432/basis` | driver psycopg 3 |
| `BASIS_TEST_DATABASE_URL` | — | usada pelos testes de integração/API |
| `BASIS_DB_PORT` | `5432` | porta publicada pelo Compose |
| `BASIS_CORS_ORIGINS` | `["http://localhost:5173"]` | JSON com as origens do frontend |
| `BASIS_AUTH__ACCESS_TOKEN_TTL_MINUTES` | `15` | validade do access token |
| `BASIS_AUTH__REFRESH_TOKEN_TTL_DAYS` | `14` | validade do refresh (cookie httpOnly) |
| `BASIS_AUTH__BOOTSTRAP_ADMIN_EMAIL/PASSWORD` | — | usados pelo `seed` para criar o primeiro admin |
| `BASIS_MARKET_DATA__ALLOW_LIVE_PROVIDERS` | `true` | provedores ao vivo em background; `false` mantém tudo no determinístico |
| `BASIS_MARKET_DATA__BRAPI_TOKEN` | — | opcional; eleva o limite do brapi.dev |
| `BASIS_MARKET_DATA__QUOTE_CACHE_TTL_SECONDS` | `60` | TTL do cache de cotações e histórico |
| `BASIS_MARKET_DATA__HTTP_TIMEOUT_SECONDS` | `5` | timeout por chamada de provedor |

Gerar segredo: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.

## Subindo do zero

```bash
cp .env.example .env                 # ajuste BASIS_SECRET_KEY e a senha do admin
docker compose up -d db              # Postgres 16 (+ basis_test criado pelo init.sql)
uv sync --directory apps/api
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api python -m basis.scripts.seed --demo   # catálogo + admin + demo
uv run --directory apps/api python -m basis                    # API em :8100
pnpm install && pnpm --filter @basis/web dev                   # web em :5174
```

O seed de demonstração cria três clientes com estratégias diferentes e ~12 meses de extrato (aportes mensais, proventos trimestrais e uma venda parcial). É idempotente: rodar de novo não duplica clientes nem instrumentos.

## Migrações

```bash
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api alembic revision --autogenerate -m "descrição"   # revisar sempre
uv run --directory apps/api alembic downgrade -1
```

Os modelos são descobertos por varredura (`basis/modules/*/infrastructure/models.py`); não é preciso registrar nada. Nunca rode migrações no boot da API.

## Contrato OpenAPI

```bash
pnpm openapi:export          # apps/api -> packages/contracts/openapi.json
pnpm contracts:generate      # openapi.json -> tipos TypeScript
pnpm openapi:export -- --check   # o CI falha se o contrato estiver desatualizado
```

## Dados de mercado

- **Ao vivo (background)**: a resposta sai imediatamente com a série determinística e o cache é atualizado pelo provedor real; o painel mostra `ao vivo` quando a origem não é o seed.
- **Offline**: `BASIS_MARKET_DATA__ALLOW_LIVE_PROVIDERS=false` — nada de rede, preços estáveis (útil para testes, CI e demonstrações).
- **Provedores**: brapi.dev (ações/FIIs/ETFs da B3), Yahoo Finance (cripto, câmbio, índices) e BCB SGS (Selic, CDI, IPCA, USD/BRL). Falha de provedor gera log `quote_provider_failed` e mantém o valor determinístico.
- **Limpar cache**: reiniciar a API (o cache é em memória, por processo).

## Backups

```bash
docker exec basis_db pg_dump -U basis -d basis -Fc -f /tmp/basis.dump
docker cp basis_db:/tmp/basis.dump ./basis-$(date +%F).dump
```

Restaurar: `pg_restore --clean --if-exists -d "$BASIS_DATABASE_URL" basis-AAAA-MM-DD.dump`.

## Incidentes comuns

| Sintoma | Diagnóstico | Ação |
|---|---|---|
| `password authentication failed` na API | a porta do host responde com **outro** Postgres (comum com vários projetos) | conferir `BASIS_DB_PORT`/`BASIS_DATABASE_URL` e `docker port basis_db` |
| API não sobe / porta ocupada | outro serviço na porta | usar `BASIS_PORT` e ajustar `VITE_API_URL`/`BASIS_CORS_ORIGINS` |
| `Psycopg cannot use the 'ProactorEventLoop'` (Windows) | loop padrão do Windows é incompatível com psycopg async | usar `python -m basis` (entrypoint que força `SelectorEventLoop`); no Linux/Docker o uvicorn padrão serve |
| Usuário "deslogado aleatoriamente" | refresh rodando em paralelo (duas abas, StrictMode) ou reuso real | esperado apenas com reuso **fora** da janela de 30 s; ver logs `refresh` e o registro em `refresh_tokens` |
| Cotações paradas em valores de seed | provedor indisponível ou `ALLOW_LIVE_PROVIDERS=false` | checar logs `quote_provider_failed`; validar rede/token do brapi |
| Primeira chamada lenta após subir | warmup de conexão/pool | aquecer com `/api/v1/health`; depois disso as respostas ficam em ms |
| `alembic upgrade` reclama de revisão inexistente | banco de outro branch | `alembic current`/`history` e alinhar com `stamp` |
| Console do navegador com keys duplicadas | listas com chave repetida | corrigir a chave (nunca índice de array em lista mutável) — houve um caso no ticker |

## Higiene e segurança

- **Trocar `BASIS_SECRET_KEY`** invalida todos os access tokens: janela de re-login em massa.
- **Sessões**: `POST /api/v1/auth/logout` revoga a sessão atual; `/logout-all` derruba todas; trocar a senha revoga tudo.
- **Segredos** nunca entram no repositório: `.env` é ignorado, `gitleaks` roda no pre-commit e no CI.
- **Dependências**: Dependabot semanal (`npm`, `pip`, `github-actions`, `docker`) + `pip-audit` no CI.
- **Repositório de refresh tokens** guarda apenas o digest SHA-256; um vazamento do banco não permite reusar tokens.

## Checklist de release

1. `pnpm turbo run lint typecheck test build` (web) e `uv run --directory apps/api pytest` (API).
2. `pnpm check` + `pnpm lint:eslint` + `pnpm knip`.
3. `pnpm openapi:export -- --check` e `pnpm contracts:generate` sem diff.
4. `docker compose --profile full up --build` numa base limpa (valida migração + seed + build).
5. Atualizar `CHANGELOG.md` e a versão em `pyproject.toml`/`package.json`.
