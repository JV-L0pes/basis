# Basis Web

SPA em React 19 + Vite + Tailwind v4 sobre o design system **Ink** (`@basis/ui`),
organizada por **Feature-Sliced Design**:

```
src/
├─ app/         providers (Query, i18n, sessão), router (TanStack), estilos
├─ pages/       dashboard · clients · portfolios · portfolio · markets · instrument · login (entrar/criar conta)
├─ widgets/     app-shell (top bar + footer) · market-ticker
├─ features/    auth · clients (cadastro, edição, suitability) · portfolios (abertura,
│               lançamento, alocação alvo)
├─ entities/    session · client · portfolio · instrument (API tipada + hooks de query)
└─ shared/      api (openapi-fetch + refresh automático) · i18n PT/EN · ui · lib · config
```

A direção das dependências (`app → pages → widgets → features → entities → shared`) é
verificada pelo ESLint; a camada `shared` nunca importa `entities` (quando precisa de
sessão, o `app` injeta via `configureAuth`).

## Comandos

```bash
pnpm install
pnpm --filter @basis/web dev        # Vite em :5174 (lê o .env da raiz do monorepo)
pnpm --filter @basis/web build      # typecheck + build de produção
pnpm --filter @basis/web test       # Vitest + Testing Library + MSW (25 testes)
pnpm --filter @basis/web lint       # Biome
pnpm lint:eslint                    # type-aware: a11y, hooks, ciclos, FSD (da raiz)
```

## Integração com a API

- O cliente HTTP único (`shared/api/client.ts`) usa `openapi-fetch` com os tipos gerados em
  `@basis/contracts`, anexa o access token em memória e, ao receber `401`, renova a sessão
  via cookie httpOnly e repete a requisição uma vez (refresh *single-flight*).
- Erros do backend chegam como `application/problem+json` (RFC 9457) e são convertidos em
  `ApiError` com `code` e `detail` legíveis — as telas mostram o problema, nunca um stack.
- `VITE_API_URL` vem do `.env` na raiz (o `envDir` do Vite aponta para lá).

## Testes

| Suíte | Cobertura |
|---|---|
| `src/pages/*/page.test.tsx` | telas com API simulada por MSW + verificação de acessibilidade (axe-core) |
| `src/features/auth/login-form.test.tsx` | validação, erro de credenciais e estado de envio |
| `src/shared/**/*.test.ts` | paridade das chaves i18n e parsing de problem details |

O router real não sobe nos testes: `@tanstack/react-router` é substituído por um stub
determinístico (`src/test/router-stub.tsx`) configurado no `vitest.config.ts`.
