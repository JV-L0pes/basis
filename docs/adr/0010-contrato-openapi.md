# ADR 0010 — Contrato OpenAPI como fonte do frontend

- Status: aceito
- Data: 2026-09-21
- Contexto: em um monorepo com dois apps, o desalinhamento entre o que a API devolve e o que o frontend espera é o defeito mais caro de encontrar — e o mais fácil de introduzir.

## Decisão

O FastAPI exporta o contrato OpenAPI 3.1 para `packages/contracts/openapi.json` (`python -m basis.scripts.export_openapi`), e `@basis/contracts` gera os tipos TypeScript com `openapi-typescript`. No frontend, toda chamada passa por `openapi-fetch` com um cliente único que trata token, refresh e erros RFC 9457. O CI roda `export_openapi --check`: contrato desatualizado quebra o build.

## Consequências

- Renomear um campo no backend gera erro de tipo no frontend antes de rodar a aplicação.
- O contrato é um artefato versionado, revisável em diff de PR.
- Custo: mudanças de API exigem `pnpm openapi:export && pnpm contracts:generate` (documentado no AGENTS.md).
