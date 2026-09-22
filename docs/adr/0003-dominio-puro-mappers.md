# ADR 0003 — Domínio puro com mappers explícitos

- Status: aceito
- Data: 2026-09-21
- Contexto: a forma mais rápida de persistir entidades é deixá-las serem os próprios modelos ORM. Também é a forma mais rápida de perder o domínio: regras vazam para o banco, testes exigem infraestrutura e a camada de domínio passa a importar SQLAlchemy.

## Decisão

O domínio é Python puro — dataclasses, value objects congelados e nenhuma dependência de framework. A persistência vive em `infrastructure/models.py` (SQLAlchemy 2.0 com `Mapped[...]`) e a tradução fica em `infrastructure/mappers.py` (`to_domain`, `to_row`, `apply_*`). Agregados são carregados e salvos inteiros; o repositório sincroniza o que mudou.

## Consequências

- Regras de negócio rodam em milissegundos nos testes unitários, sem banco nem container.
- O `import-linter` proíbe SQLAlchemy/FastAPI/Pydantic dentro de qualquer `domain/`.
- Custo real: mapeamento manual. Compensado por menos bugs de lazy-load e por entidades que não carregam uma sessão viva nas costas.
