# Arquitetura

Este documento explica **por que** o Basis está organizado como está, quais
convenções de mercado adota e onde estender.

---

## 1. Estilo arquitetural

**Monolito modular com DDD tático.** Cada contexto é um módulo com fronteira
explícita; toda comunicação entre contextos acontece por contratos publicados
(protocolos + DTOs) ou por eventos de domínio — nunca por acesso direto a tabelas
ou entidades de outro contexto.

Motivações:

- um único artefato para implantar (custo operacional baixo, comum em times
  pequenos), com caminho de extração para serviços se necessário;
- transações ACID por caso de uso, sem sagas para operações simples;
- fronteiras verificáveis automaticamente (ver §4), o que evita o "monolito
  acoplado" que degrade com o tempo.

### Camadas

```
presentation → application → domain
infrastructure ───────────→ domain
```

| Camada | Contém | Não pode conter |
| --- | --- | --- |
| `domain` | entidades, value objects, agregados, eventos, serviços de domínio, portas | SQLAlchemy, FastAPI, Pydantic, outro contexto |
| `application` | casos de uso, DTOs, orquestração, publicação de eventos | SQL direto, HTTP |
| `infrastructure` | modelos ORM, repositórios, providers externos, mapeadores | regra de negócio |
| `presentation` | rotas, schemas de request/response, composição de dependências | regra de negócio |

O `presentation` é o *composition root*: os provedores de dependência
(`presentation/dependencies.py`) montam repositórios, casos de uso e serviços.

---

## 2. Contextos delimitados

| Contexto | Responsabilidade | Publica |
| --- | --- | --- |
| `identity` | usuários, credenciais, sessões, papéis | `UserRegistered`, `UserPasswordChanged`, `UserDeactivated` |
| `clients` | investidores, CPF/CNPJ, questionário de suitability | `ClientSummary` (diretório), `ClientRegistered`, `ClientArchived` |
| `portfolio` | carteiras, extrato, posições, alocação alvo, valuação | `PortfolioSnapshot` (leitura consolidada), `TransactionRecorded` |
| `market_data` | instrumentos, cotações, séries macro, providers | `InstrumentSummary`, `QuoteView`, `IndexPointView` |
| `analytics` | performance, risco, drift de alocação, rebalanceamento | relatórios derivados (sem estado próprio) |

### Direção das dependências entre contextos

```
analytics ──► portfolio (PortfolioReader)  ──► market_data (QuoteProvider)
    │              │                                 ▲
    └──────────────┴──► market_data (InstrumentCatalog) ┘
portfolio ──► clients (ClientDirectory)
```

Todas essas dependências são **protocolos publicados**, implementados na
infraestrutura do contexto dono. `analytics`, por exemplo, define seu próprio
vocabulário (`PricedPosition`, `AllocationTarget`) e a camada de aplicação
traduz `PortfolioSnapshot` para esses tipos — é isso que mantém os domínios
independentes (contrato verificado pelo import-linter).

### Tabelas por contexto

O banco é único, mas **não há chave estrangeira entre contextos**: `portfolios.client_id`
é uma referência lógica validada na aplicação (`ClientDirectory`), não uma FK.
Assim, um contexto pode ser extraído para outro banco sem cirurgia no schema.
Fks existem apenas dentro do contexto (`portfolio_targets` e
`portfolio_transactions` → `portfolios`).

---

## 3. Fronteira de escrita e leitura

- **Escrita** sempre por agregados: `Portfolio` carrega todo o extrato e deriva
  posições por fold determinístico (`Position.apply`). Isso elimina o bug clássico
  de posição dessincronizada do extrato.
- **Leitura** por projeções: `PortfolioSnapshot` entrega posições já somadas para
  o `analytics`, que as recombina com históricos de preço para calcular retornos.
- O extrato é *append-only*; o repositório sincroniza apenas o que foi
  acrescentado/removido, preservando os identificadores.

Trade-off assumido: carregar o extrato inteiro não escala para carteiras com
milhares de lançamentos. A evolução natural é um *snapshot* periódico de posições
materializado, mantendo o extrato como fonte da verdade.

---

## 4. Fronteiras verificadas em CI

`import-linter` (configurado em `apps/api/pyproject.toml`) garante:

1. camadas do kernel apontam para dentro;
2. domínios de contextos diferentes são **independentes**;
3. domínio é Python puro (sem SQLAlchemy, FastAPI, Pydantic ou structlog);
4. cada contexto respeita sua própria ordem de camadas.

No frontend, `biome` cobre estilo e lint; a estrutura FSD é sustentada por
convenção e revisão (o custo de um plugin de fronteiras não se paga neste porte).

---

## 5. Convenções do mercado financeiro

| Tema | Decisão |
| --- | --- |
| Dinheiro | `Decimal` com escala 12 no kernel, `NUMERIC(28,10)` no banco, string no JSON |
| Arredondamento | half-even (bancário) na menor unidade da moeda |
| Alocação de sobras | método do maior resto — a soma dos rateios é exatamente o total |
| Identificação | ISIN (ISO 6166 + Luhn), MIC (ISO 10383), CFI (ISO 10962), FIGI como evolução |
| Documentos BR | CPF/CNPJ com validação mod-11 completa e máscara segura para exibição |
| Moedas | ISO 4217 + unidades cripto (expoente próprio: BTC 8, ETH 18) |
| Datas | ISO 8601/RFC 3339, sempre com fuso; `Clock` injetável |
| Retorno ponderado no tempo | TWR por sub-períodos diários, fluxos externos neutralizados |
| Retorno ponderado pelo dinheiro | XIRR (Newton-Raphson com fallback de bisseção, day count actual/365) |
| Risco | volatilidade anualizada (√252), Sharpe, beta vs. Ibovespa, drawdown máximo, VaR histórico 95% |
| Taxa livre de risco | Selic anualizada a partir da série diária do BCB (SGS 11) |
| Suitability | questionário pontuado (0–4 por resposta) → perfil, com reavaliação auditável |

### Premissas do cálculo de performance

Documentadas em `analytics/application/valuation.py`:

- compras são aportes externos e vendas são retiradas (fluxos externos);
- dividendos, juros e taxas permanecem como caixa dentro da carteira;
- ativos sem preço de mercado são marcados pelo custo médio;
- o benchmark padrão é o Ibovespa (Yahoo `^BVSP`).

---

## 6. Dados de mercado

`market_data` traz três providers atrás de um protocolo único, com roteamento por
formato de símbolo, cache TTL e fallback:

| Provider | Cobre | Observação |
| --- | --- | --- |
| brapi.dev | ações, FIIs e ETFs da B3 | token opcional (`BASIS_MARKET_DATA__BRAPI_TOKEN`) eleva o limite de requisições |
| Yahoo Finance | cripto, câmbio e índices | endpoint público; símbolos mapeados (`BTC` → `BTC-USD`) |
| BCB SGS | Selic, CDI, IPCA, USD/BRL | dados oficiais do Banco Central |
| Seed | tudo | determinístico, usado em testes e quando `ALLOW_LIVE_PROVIDERS=false` |

Falha de provider nunca vira erro 500: o roteador registra um aviso e cai para o
provider determinístico, mantendo a aplicação utilizável offline.

---

## 7. Segurança

- Argon2id com parâmetros configuráveis (padrão OWASP) e re-hash transparente.
- Access token JWT curto (15 min) mantido **apenas em memória** no frontend;
  refresh token opaco, rotativo, persistido como SHA-256 e entregue em cookie
  `httpOnly` + `SameSite=Lax` (caminho restrito a `/api/v1/auth`).
- Reuso de refresh token revoga toda a família de sessões (resposta a roubo).
- Login com tempo equalizado (hash fictício quando o e-mail não existe) para
  evitar enumeração de contas.
- Erros de domínio não vazam stack; detalhes técnicos só com `BASIS_DEBUG=true`.
- `gitleaks` no pre-commit e no CI; `pip-audit` no CI; Dependabot semanal.

---

## 8. Decisões registradas

| Decisão | Alternativas descartadas | Motivo |
| --- | --- | --- |
| Postgres | MySQL (banco do projeto original) | `NUMERIC` exato, JSONB, matviews, testcontainers |
| SQLAlchemy 2 async + psycopg 3 | asyncpg | um driver para sync (Alembic) e async (app) |
| Domain puro + mappers explícitos | entidades ORM | domínio testável sem banco e fronteira de camadas verificável |
| Keyset pagination | offset | estável sob inserções, índice denso com UUIDv7 |
| Eventos in-process | broker externo | transação única; extração para broker é evolução natural |
| Vite + React SPA | manter Next.js | app autenticado não se beneficia de RSC; build e DX mais simples |
| Radix + Tailwind (estilo shadcn) | Base UI | estabilidade e documentação dos primitivos |

---

## 9. Próximos passos sugeridos

1. **Multi-moeda**: conversão via PTAX para carteiras com ativos internacionais.
2. **Renda fixa**: curvas, PU, marcação a mercado e day count por título
   (hoje a renda fixa é tratada como preço unitário).
3. **Open Finance / CVM**: ingestão de extratos e posições via APIs reguladas.
4. **Snapshots de posição** para carteiras com extrato longo.
5. **Extração de contexto** para serviço quando um módulo exigir escala própria
   (o `analytics` é o candidato natural, por ser somente leitura).
6. **Observabilidade**: OpenTelemetry com traces por caso de uso e métricas de
   latência de providers.
