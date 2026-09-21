# Basis API

FastAPI modular monolith built with domain-driven design. Every bounded context
lives under `src/basis/modules/<context>` with `domain`, `application`,
`infrastructure` and `presentation` layers; shared building blocks live under
`src/basis/kernel`.

Architecture rules are enforced in CI by `import-linter` (see the contracts in
`pyproject.toml`) and by `ruff`/`mypy`.

## Commands

```bash
uv sync                              # install dependencies
uv run uvicorn basis.main:app --reload
uv run alembic upgrade head          # apply migrations
uv run python -m basis.scripts.seed  # seed instruments + demo data
uv run pytest                        # unit + integration + API tests
uv run ruff check . && uv run mypy src
uv run lint-imports                  # architecture boundaries
```

Configuration uses the `BASIS_` environment prefix; see `.env.example` at the
repository root.
