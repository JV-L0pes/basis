# ADR 0002 — DDD com bounded contexts e fronteiras verificadas

- Status: aceito
- Data: 2026-09-21
- Contexto: o produto cobre áreas com vocabulários distintos — identidade, clientes, carteiras, mercado e analytics. Misturar esses conceitos é o caminho mais curto para um domínio anêmico.

## Decisão

Cinco bounded contexts, cada um com quatro camadas (`domain`, `application`, `infrastructure`, `presentation`) e dependências apontando para dentro:

| Contexto | Responsabilidade | Publica para os outros |
|---|---|---|
| `identity` | usuários, sessões, papéis | eventos de registro |
| `clients` | investidores, CPF/CNPJ, suitability | `ClientDirectory` (resumo do cliente) |
| `portfolio` | carteiras, extrato, posições, alvos | `PortfolioReader` (snapshot consolidado) |
| `market_data` | instrumentos, cotações, macro | `InstrumentCatalog`, `QuoteProvider`, `MacroProvider` |
| `analytics` | performance, risco, drift | relatórios derivados (sem estado) |

Integração entre contextos acontece por **contratos publicados** (protocolos + DTOs) ou eventos de domínio — nunca por acesso direto às tabelas do vizinho. Não existe chave estrangeira entre contextos: `portfolios.client_id` é uma referência lógica validada pelo `ClientDirectory`.

## Consequências

- `analytics` possui o próprio vocabulário (`PricedPosition`, `AllocationTarget`) e traduz o snapshot na camada de aplicação — por isso os domínios permanecem independentes.
- O `import-linter` reprova o build quando um domínio importa outro contexto, SQLAlchemy, FastAPI ou Pydantic.
- Custo: um pouco mais de mapeamento; benefício: o domínio é testável sem banco e a fronteira é um contrato de CI, não um combinado verbal.
