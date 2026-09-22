# Basis API

FastAPI + SQLAlchemy 2.0 assíncrono, organizado como **monolito modular com DDD**: cada
bounded context (`identity`, `clients`, `portfolio`, `market_data`, `analytics`) tem
`domain` / `application` / `infrastructure` / `presentation`, e as fronteiras são
verificadas por `import-linter` no CI.

## Comandos

```bash
uv sync                                                    # dependências
uv run alembic upgrade head                                # migrações
uv run python -m basis.scripts.seed --demo                 # catálogo + admin + demo
uv run python -m basis                                     # dev server (:8100, SelectorEventLoop no Windows)
uv run uvicorn basis.main:app --reload                     # Linux/Docker
uv run python -m basis.scripts.export_openapi              # contrato para packages/contracts
uv run pytest                                              # 470 testes: domain, integration, API
uv run ruff check . && uv run ruff format --check .
uv run mypy src tests
uv run lint-imports                                        # 8 contratos de arquitetura
```

## Layout

```
src/basis/
├─ kernel/                      shared kernel: Money, Currency, Entity/AggregateRoot,
│                               eventos, Clock, erros RFC 9457, DB, HTTP, paginação
├─ modules/<context>/
│  ├─ domain/                   entidades, value objects, eventos, portas (Python puro)
│  ├─ application/              casos de uso, DTOs, publicação de eventos
│  ├─ infrastructure/           modelos SQLAlchemy, repositórios, mappers, providers
│  └─ presentation/             rotas, schemas, composition root (dependencies.py)
└─ scripts/                     seed, export do OpenAPI
```

Regras de camada que o CI garante: `domain` nunca importa SQLAlchemy/FastAPI/Pydantic nem
outro contexto; `presentation` monta as dependências; erros de domínio viram problem
details automaticamente.

## Configuração

Tudo por ambiente, prefixo `BASIS_` e `__` para aninhamento (ex.:
`BASIS_AUTH__ACCESS_TOKEN_TTL_MINUTES`). A lista completa está em `.env.example` na raiz
do repositório e no [runbook](../../docs/runbook/operacao.md).

## Testes

| Camada | O que cobre | Onde |
|---|---|---|
| `tests/unit` | regras de domínio, casos de uso com fakes, mappers, providers com `respx` | 14 arquivos |
| `tests/integration` | repositórios contra Postgres real (transação revertida por teste) | 3 arquivos |
| `tests/api` | fluxos HTTP completos com TestClient (auth, clientes, carteiras, mercado, analytics) | 4 arquivos |

Os testes de integração/API usam `BASIS_TEST_DATABASE_URL`; os de API desligam provedores
ao vivo para não tocar a rede.
