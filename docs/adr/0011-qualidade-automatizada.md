# ADR 0011 — Qualidade automatizada como contrato de merge

- Status: aceito
- Data: 2026-09-22
- Contexto: projeto solo, sem revisor humano. Regra que não é verificada por ferramenta é regra que vai ser quebrada — e o legado deste repositório era exatamente isso: sem lint, sem tipos, sem testes.

## Decisão

Cada garantia tem uma ferramenta e um portão de CI:

| Garantia | Ferramenta | Onde roda |
|---|---|---|
| Formatação e lint base (TS/JSON/CSS) | Biome | CI, pre-commit |
| Lint type-aware, a11y, hooks, ciclos, FSD | ESLint 9 flat config | CI |
| Código/dependência morta | Knip | CI |
| Tipos do backend | mypy strict (160 arquivos) | CI |
| Segurança Python (bandit/S) e estilo | Ruff | CI, pre-commit |
| Fronteiras entre contextos | import-linter (8 contratos) | CI |
| Contrato OpenAPI em dia | `export_openapi --check` | CI |
| Regras de negócio | pytest (domínio, integração, HTTP) | CI com Postgres real |
| Componentes e páginas | Vitest + Testing Library + MSW | CI |
| Acessibilidade | axe-core nos testes de página | CI |
| Segredos e CVEs | gitleaks, pip-audit | CI, pre-commit |

## Consequências

- Nenhuma regra é "combinado verbal": ou é um contrato no CI, ou é um teste.
- O ESLint pegou uma violação real de FSD (camada `shared` importando `entities`) que passou despercebida na revisão manual — a correção foi injeção pelo `app` (`configureAuth`).
- Custo: pipeline mais lento (~3 min) e configuração que precisa ser mantida junto com as dependências (ex.: pin de `vite` para alinhar tipos de vitest).
