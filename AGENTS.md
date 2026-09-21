# AGENTS.md

Guia para pessoas e agentes que trabalham neste repositório. Vale para o
monorepo inteiro; regras específicas estão nos READMEs de cada pacote.

---

## Comandos essenciais

```bash
# Frontend / TS (na raiz)
pnpm install
pnpm turbo run lint typecheck test build
pnpm check                 # biome format+lint em todo o monorepo
pnpm lint:eslint           # eslint type-aware (a11y, sonarjs, FSD, ciclos)
pnpm knip                  # código e dependências mortas
pnpm --filter @basis/ui test
pnpm --filter @basis/web dev

# Backend (na raiz, via uv)
uv run --directory apps/api ruff check . --fix
uv run --directory apps/api ruff format .
uv run --directory apps/api mypy src tests
uv run --directory apps/api lint-imports      # fronteiras de arquitetura
uv run --directory apps/api pytest
uv run --directory apps/api alembic upgrade head
uv run --directory apps/api python -m basis.scripts.seed --demo
uv run --directory apps/api python -m basis.scripts.export_openapi --check

# Contrato
pnpm openapi:export && pnpm contracts:generate
```

No Windows, se `uv` não estiver no PATH: `$env:Path = "C:\Users\<você>\.local\bin;$env:Path"`.
Para subir a API no Windows use `uv run --directory apps/api python -m basis`
(psycopg async exige event loop `Selector`).

**Antes de considerar qualquer tarefa concluída:** `ruff`, `mypy`, `lint-imports`
e `pytest` verdes no backend; `biome`, `lint:eslint`, `knip`, `typecheck` e
`vitest` verdes no frontend.

---

## Estrutura

```
apps/api/src/basis/kernel        shared kernel (Money, Currency, Entity, eventos, DB, HTTP)
apps/api/src/basis/modules/<ctx> bounded contexts (identity, clients, portfolio, market_data, analytics)
apps/api/tests/{unit,integration,api}
apps/web/src                     FSD: app · pages · widgets · features · entities · shared
packages/ui                      design system Ink + primitivos
packages/contracts               openapi.json + tipos gerados
```

---

## Regras do backend

1. **Camadas.** `domain` não importa SQLAlchemy/FastAPI/Pydantic nem outro
   contexto. `application` orquestra. `infrastructure` persiste. `presentation`
   expõe HTTP. O `lint-imports` reprova violações — não as burle com `# type: ignore`.
2. **Domínio puro e testável.** Entidades são dataclasses (`eq=False, slots=True`)
   que estendem `Entity`/`AggregateRoot`; value objects são `frozen=True`.
   Regras de negócio vivem em métodos do agregado e em serviços de domínio, nunca
   em repositórios ou rotas.
3. **Dinheiro** sempre `Money` (Decimal). Nunca `float`. Divisões passam por
   `Money.__truediv__`, que limita a 12 casas.
4. **Tempo** sempre pelo `Clock` injetado; `datetime.now` é bloqueado pelo Ruff.
5. **Escreva casos de uso** como classes com `execute`, recebendo repositórios,
   `Clock`, `UnitOfWork` e `EventPublisher` por construtor. Publique eventos
   **depois** de `await uow.commit()`.
6. **Provedores de dependência** ficam em `presentation/dependencies.py` e usam
   `Annotated[..., Depends(...)]` do kernel (`SessionDep`, `ClockDep`, ...).
7. **Erros** são `BasisError` do kernel (com `code` e `http_status`); a camada HTTP
   converte para RFC 9457 automaticamente. Não levante `HTTPException`.
8. **Repositórios** mapeiam linha ↔ domínio em `infrastructure/mappers.py`; nunca
   devolva modelos ORM para fora do repositório.
9. **Tabelas novas** exigem migração Alembic (`pnpm db:migrate`), teste de
   integração e inclusão no schema de testes (automática via metadata).
10. **Sem comentários óbvios.** Comente apenas decisões não triviais (uma linha,
    em inglês). Docstrings explicam o *porquê*, não o *o quê*.

## Regras do frontend

1. **FSD.** `shared` não importa de camadas superiores; `entities` não importam
   `features`/`pages`; `pages` compõem `widgets`/`features`/`entities`. O ESLint
   reprova violações (`no-restricted-imports` por camada). Quando `shared`
   precisar de algo de camada superior (ex.: token de sessão), injete pelo
   `app` (ver `configureAuth` em `shared/api/client.ts`).
2. **Todo dado do servidor** passa por TanStack Query; `shared/api/client.ts`
   cuida de token e refresh. Não use `fetch` direto em componentes.
3. **Formulários** com react-hook-form + zod; mensagens de erro sempre pelo `t()`.
4. **Todo texto visível** vem do dicionário i18n (`pt` é a fonte; `en` precisa ter
   as mesmas chaves — há teste garantindo paridade).
5. **Design system**: use `@basis/ui`; não invente cores/sombras. O ouro é
   reservado para status/valor; radius 0 exceto pills; zero sombras.
6. **Acessibilidade**: elementos interativos com `aria-*`, foco visível,
   `prefers-reduced-motion` respeitado. Rode o Biome antes de commitar.
7. **Chaves de componente** estáveis (nunca índice de array em listas mutáveis).

---

## Convenções de código

- Código em **inglês** (identificadores, commits, docstrings). Documentação de
  produto em **português**.
- Python: `from __future__ import annotations`, tipos completos, PEP 695 para
  genéricos, `ruff format` (100 colunas).
- TypeScript: `strict`, `verbatimModuleSyntax`, sem `any`; `import type` para tipos.
- Commits: `feat|fix|refactor|test|docs|chore(escopo): mensagem` (Conventional Commits).
- Um PR por incremento; descreva o comportamento observável e os testes adicionados.

---

## Armadilhas conhecidas

- **Windows + psycopg async**: sem loop `Selector` a conexão falha. Use o
  entrypoint `python -m basis`, e nos testes o `conftest` já configura.
- **Porta 5432 ocupada**: defina `BASIS_DB_PORT` e `BASIS_DATABASE_URL` no `.env`.
- **Alembic**: os modelos são descobertos por varredura (`pkgutil`) em
  `basis/modules/*/infrastructure/models.py`. Crie o arquivo com esse nome para
  que a migração automática o encontre.
- **OpenAPI desatualizado** quebra o CI: rode `pnpm openapi:export` e
  `pnpm contracts:generate` ao mudar rotas ou schemas.
- **Dinheiro em JSON** é string (exata) mais `numeric` (aproximação para gráficos).
  Não recalcule dinheiro no cliente.
