# Case study — Basis

> De um case de processo seletivo (Fastify + Prisma + Next.js, catálogo hardcoded e nenhum teste)
> a uma plataforma de gestão de investimentos com domínio financeiro de verdade:
> DDD em cinco contextos, matemática de performance auditável e design system próprio.

Autor: João Victor Lopes ([JV-L0pes](https://github.com/JV-L0pes)).

## O problema

O repositório original (`AnkaTechCase`) era um CRUD de demonstração: dois modelos (`Client` e `Asset`), três telas e um catálogo de "oportunidades" com sete ativos **hardcoded em TypeScript**. Nada ali sobrevivia a um dia de uso real:

- **não havia domínio**: `Asset.value` significava "valor investido" numa tela e "cotação" em outra; comprar ações era inserir uma linha com nome e preço digitados à mão;
- **não havia conta**: qualquer pessoa chamava a API; não existia usuário, sessão ou papel;
- **não havia verificação**: zero testes, zero lint, zero tipos nos limites, `prisma db push --accept-data-loss` a cada boot;
- **não havia mercado**: nenhuma cotação real, nenhuma série histórica, nenhum indicador macroeconômico — apesar do nome "Investment Management Platform".

O objetivo do revamp não era "consertar o CRUD", e sim responder à pergunta que um investidor faz de verdade: **por que confiar neste número?** Rentabilidade, alocação e risco só valem se forem reconstruíveis a partir de fatos do extrato e de preços de mercado.

## O que foi construído

Uma plataforma completa de acompanhamento de carteiras para o mercado brasileiro, em um monolito modular com cinco bounded contexts:

- **Identidade e acesso**: Argon2id, JWT curto em memória + refresh opaco rotativo em cookie httpOnly, papéis (admin/advisor/viewer), troca de senha que revoga sessões e cadastro de conta pela própria interface (primeiro usuário vira admin, os demais advisor) — qualquer avaliador consegue entrar sem usar as credenciais do seed.
- **Clientes**: validação real de CPF/CNPJ (dígitos verificadores), questionário de suitability que vira perfil de risco (conservador/moderado/arrojado), busca, arquivamento reversível.
- **Carteiras**: extrato append-only de compras, vendas, proventos e taxas; posições derivadas por custo médio ponderado; alocação alvo em basis points; valoração mark-to-market com P&L por posição.
- **Mercado**: catálogo com ISIN/MIC/CFI, cotações de brapi.dev, Yahoo Finance e BCB SGS com cache, fallback determinístico e atualização em background; séries macro (Selic, CDI, IPCA, USD/BRL); histórico para gráficos.
- **Analytics**: TWR, XIRR, volatilidade anualizada, Sharpe (Selic como taxa livre de risco), beta vs. Ibovespa, drawdown máximo, VaR 95%, alocação atual vs. alvo com drift em bps e plano de rebalanceamento.

O frontend é uma SPA em React 19 com Feature-Sliced Design, construída sobre o design system **Ink** (o mesmo do portfólio), com tema claro/escuro, i18n PT/EN e gráficos em SVG próprio.

## Decisões que definem o projeto

Cada decisão tem um ADR em [`docs/adr/`](adr/).

1. **Monolito modular com DDD, não microsserviços** (ADR 0001/0002). Cinco contexts, quatro camadas, integração por contratos publicados (`ClientDirectory`, `PortfolioReader`, `InstrumentCatalog`, `QuoteProvider`) e **8 contratos de fronteira verificados por `import-linter` no CI**. Um deploy, fronteiras explícitas, extração futura mecânica.
2. **Domínio puro, persistência mapeada à mão** (ADR 0003). Nenhuma entidade é um modelo ORM: as regras rodam em milissegundos nos testes, sem banco, e o CI reprova SQLAlchemy/FastAPI/Pydantic dentro de `domain/`.
3. **Dinheiro nunca é float** (ADR 0004). `Money` sobre `Decimal`, escala máxima de 12 casas, arredondamento bancário, rateio pelo maior resto (`sum(partes) == total` sempre), `NUMERIC(28,10)` no Postgres e string exata no JSON.
4. **Padrões abertos de mercado** (ADR 0005): ISO 4217 (moedas), ISO 8601 (datas), ISO 6166 (ISIN com Luhn), ISO 10962 (CFI), ISO 10383 (MIC), CPF/CNPJ mod-11, UUIDv7. Nada de "tipo: Ação" em texto livre.
5. **Matemática financeira como calculadora pura** (ADR 0006). TWR por sub-períodos, XIRR com Newton-Raphson + bisseção, riscos clássicos — tudo em funções sem I/O, com vetores conhecidos nos testes (ex.: −1000 hoje e +1100 em 365 dias ⇒ 10% a.a.).
6. **Mercado ao vivo sem bloquear a tela** (ADR 0007). A resposta sai na hora com a série determinística e o cache é atualizado pelo provedor em background (stale-while-revalidate).
7. **Sessão que sobrevive a duas abas** (ADR 0008). Refresh rotativo com detecção de reuso **e** janela de graça de 30 s: corrida de cliente não derruba a sessão, roubo derruba a família inteira.
8. **O design do portfólio virou produto** (ADR 0009). Ink em `packages/ui`: tokens, primitivos estilo shadcn sobre Radix, gráficos próprios em SVG (linha com crosshair por teclado, donut, sparkline) e `lightweight-charts` só para candles.
9. **Contrato OpenAPI como fonte do frontend** (ADR 0010). Tipos gerados do `openapi.json`; campo renomeado no backend quebra o build do frontend antes de rodar.
10. **Qualidade como contrato de merge** (ADR 0011). Biome + ESLint type-aware (a11y, hooks, ciclos, **fronteiras FSD**) + Knip + Ruff/bandit + mypy strict + import-linter + pytest + Vitest + axe-core, todos no CI.

## Arquitetura

```
┌───────────────────────┐   /api/v1/*    ┌──────────────────────────────────────────┐
│  SPA (React 19)       │ ─────────────► │  API única (FastAPI + SQLAlchemy async)  │
│  FSD + Ink + Query    │ ◄───────────── │  identity · clients · portfolio ·        │
│  i18n PT/EN · charts  │   RFC 9457     │  market_data · analytics                 │
└───────────────────────┘                └───────────────┬──────────────────────────┘
        ▲                                                │
        │ tipos gerados                                  │ NUMERIC + Decimal
        │ do OpenAPI 3.1                                 ▼
┌───────┴───────────────┐                ┌──────────────────────────────────────────┐
│  @basis/contracts     │                │  Postgres 16                             │
│  @basis/ui (Ink)      │                │  extrato append-only · catálogo · sessão │
└───────────────────────┘                └──────────────────────────────────────────┘
                                                 ▲
                                                 │ brapi · Yahoo · BCB (background)
```

- **Frontend (FSD)**: `app → pages → widgets → features → entities → shared`, com TanStack Router/Query, formulários react-hook-form + zod e camada HTTP única (`openapi-fetch`) que renova o token sozinha. MSW nos testes de página e axe-core para acessibilidade.
- **Backend**: um agregado por contexto, casos de uso explícitos, repositórios sobre SQLAlchemy 2.0 async, eventos de domínio publicados após o commit, erros de domínio convertidos para RFC 9457 com `X-Request-ID`.
- **Extrato como fonte da verdade**: posições não são armazenadas — são o *fold* do extrato (custo médio ponderado). Não existe o bug clássico de posição dessincronizada.

## Qualidade e verificação

- **519 testes**: 470 na API (domínio, integração com Postgres real e HTTP), 25 no web (páginas com MSW + login + i18n) e 24 no design system (formatadores, componentes, gráficos).
- **8 contratos de arquitetura** no `import-linter` e **8 verificações de CI** (Biome, ESLint, Knip, Ruff, mypy strict, contrato OpenAPI, pytest, gitleaks/pip-audit).
- **Regras catalogadas** em [`docs/domain/catalogo.md`](domain/catalogo.md): 24 regras de negócio (RN) e 15 de mercado/analytics (RM), cada uma rastreada até o teste que a protege.
- **Latência medida**, não estimada: `/portfolios` 12,5 s → 26 ms, `/market/overview` 12,7 s → 13 ms, `/performance` 10 s → 0,7 s.

## Problemas interessantes resolvidos no caminho

- **Escala do Decimal**: dividir custo total por quantidade gera dízimas (`2618 / 30`). O kernel passou a limitar o resultado a 12 casas em vez de estourar a validação — o bug apareceu ao comprar IGUATEMI11 na demo.
- **Taxa livre de risco de 8×10¹⁴**: o `latest` de uma série macro usava uma janela de 100 anos e o provider determinístico *somava* a Selic diária; o Sharpe saiu em `-5e15`. Corrigido com delegação ao `latest` de cada provedor, semântica de taxa por período (BCB) e um teste de regressão.
- **Deslogar ao clicar na logo**: o efeito duplo do React StrictMode disparava dois `/auth/refresh`; o segundo encontrava o cookie já rotacionado e a detecção de reuso matava a sessão. Solução em duas camadas: refresh *single-flight* no cliente e janela de graça de 30 s no servidor.
- **12 segundos de tela em branco**: provedores ao vivo com timeout + retry em série. Trocado por stale-while-revalidate com chamadas concorrentes, `bisect` na série de preços e timeout de 5 s.
- **PSycopg × Windows**: o loop `ProactorEventLoop` é incompatível com psycopg async; o entrypoint de desenvolvimento força `SelectorEventLoop` e o runbook documenta o sintoma.
- **Fronteira furada**: o ESLint (FSD por camada) pegou `shared/api` importando o store de `entities`; a correção foi injetar a sessão pelo `app` (`configureAuth`), mantendo a direção das dependências.
- **Tipos de vitest × vite**: duas cópias de Vite no store quebravam o tipo de `defineConfig`; resolvido fixando o Vite via `pnpm.overrides` e documentando no commit.

## Resultados

- O número na tela é reconstruível: posição é o fold do extrato, rentabilidade é TWR/XIRR sobre preços de mercado, alocação é percentual do valor a mercado.
- A plataforma funciona **offline** (série determinística) e **ao vivo** (background), sem mudar uma linha de domínio.
- Interface com identidade própria: tema claro/escuro, i18n PT/EN, tabelas-ledger com numerais tabulares e gráficos em SVG no vocabulário Ink.
- **Limitações assumidas**: sem multi-moeda (ativos em USD não são convertidos via PTAX), renda fixa tratada como preço unitário (sem curva, PU ou day count BUS/252), sem conta corrente modelada (proventos ficam como caixa interno), extrato carregado inteiro por carteira (snapshot de posições é a evolução natural) e sem observabilidade distribuída.
- Próximos passos sugeridos: PTAX/multi-moeda, curvas de renda fixa, snapshots materializados, Open Finance/CVM e OpenTelemetry.

## Links

- [README](../README.md) · [Changelog](../CHANGELOG.md)
- [ADRs](adr/) · [Catálogo de regras](domain/catalogo.md) · [Runbook](runbook/operacao.md)
- [Arquitetura](../ARCHITECTURE.md)
