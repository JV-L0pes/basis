# @basis/contracts

Contrato HTTP compartilhado entre a API e o frontend.

- `openapi.json` — OpenAPI 3.1 gerado pelo FastAPI (`pnpm openapi:export`), versionado para revisão em PR.
- `src/generated/schema.d.ts` — tipos TypeScript gerados por `openapi-typescript`.
- `src/index.ts` — reexporta `paths`, `components` e `operations`.

## Uso

```ts
import type { components, paths } from "@basis/contracts"
import createClient from "openapi-fetch"

const api = createClient<paths>({ baseUrl: import.meta.env.VITE_API_URL })
const { data } = await api.GET("/api/v1/portfolios")
type Portfolio = components["schemas"]["PortfolioResponse"]
```

## Fluxo

```bash
pnpm openapi:export        # FastAPI -> openapi.json
pnpm contracts:generate    # openapi.json -> tipos TypeScript
pnpm openapi:check         # o CI falha se o contrato estiver desatualizado
```

Regra do projeto: mudar uma rota ou schema sem regenerar o contrato quebra o CI — assim o
frontend nunca fica desalinhado do backend (ver ADR 0010).
