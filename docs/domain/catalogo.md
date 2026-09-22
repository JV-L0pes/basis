# Catálogo de regras — Basis

Rastreabilidade entre regra de domínio, implementação e teste. Toda regra listada
aqui tem um teste que a protege; regra nova entra com teste no mesmo PR.

- **RN** — regra de negócio (identidade, clientes, carteiras)
- **RM** — regra de mercado/analytics (instrumentos, cotações, performance, risco)

## Identidade (RN-01…RN-06)

| Regra | Implementação | Teste |
|---|---|---|
| RN-01 primeiro usuário cadastrado vira `admin`; os demais `advisor` | `identity/application/use_cases.py` (`RegisterUser`) | `tests/unit/test_identity_use_cases.py` |
| RN-02 senha com ≥10 caracteres, letra, dígito e fora da lista de senhas comuns | `identity/domain/value_objects.py` (`PasswordPolicy`) | `tests/unit/test_identity_domain.py` |
| RN-03 e-mail normalizado (minúsculas) e único por usuário | `Email` + `users.email` unique | `test_identity_domain.py`, `tests/api/test_auth_api.py` |
| RN-04 login com tempo equalizado e Argon2id com re-hash transparente | `Argon2idHasher`, `AuthenticateUser` | `tests/unit/test_identity_tokens.py`, `test_auth_api.py` |
| RN-05 refresh rotativo: reuso encerra a família; reuso em até 30 s é corrida e preserva a sessão | `RefreshSession` + `ROTATION_GRACE_SECONDS` | `test_identity_use_cases.py`, `test_auth_api.py` |
| RN-06 trocar a senha revoga todas as sessões; desativar conta bloqueia login | `ChangePassword`, `User.deactivate` | `test_identity_use_cases.py`, `test_identity_domain.py` |

## Clientes (RN-07…RN-14)

| Regra | Implementação | Teste |
|---|---|---|
| RN-07 CPF/CNPJ com dígitos verificadores mod-11; sequências repetidas recusadas | `clients/domain/value_objects.py` (`TaxId`) | `tests/unit/test_clients_domain.py` |
| RN-08 documento sempre mascarado na API e no `str()` | `TaxId.masked`, `ClientView` | `test_clients_domain.py`, `tests/api/test_clients_api.py` |
| RN-09 documento único → `409 conflict` com o documento mascarado | `RegisterClient` + índice único | `tests/unit/test_clients_use_cases.py`, `test_clients_api.py` |
| RN-10 nome 2…120 caracteres, sem dígitos, com espaços normalizados | `PersonName` | `test_clients_domain.py` |
| RN-11 questionário de suitability: 5…10 respostas de 0 a 4 → score 0…100 | `SuitabilityAssessment` | `test_clients_domain.py` |
| RN-12 perfil: score < 35 conservador, < 70 moderado, senão arrojado | `SuitabilityAssessment.profile` | `test_clients_domain.py` |
| RN-13 cliente arquivado é imutável (editar/reavaliar ⇒ `422 invariant_violation`) | `Client._ensure_active` | `test_clients_domain.py`, `tests/api/test_clients_api.py` |
| RN-14 observações com até 500 caracteres; texto em branco vira `null` | `Client` | `test_clients_domain.py` |

## Carteiras (RN-15…RN-24)

| Regra | Implementação | Teste |
|---|---|---|
| RN-15 alocação alvo soma exatamente 10000 bps (ou vazia); uma classe por vez | `AllocationTargets`, `TargetAllocation` | `tests/unit/test_portfolio_domain.py` |
| RN-16 lançamento exige quantidade > 0, preço ≥ 0 e moeda igual à do instrumento | `Transaction.record` | `test_portfolio_domain.py` |
| RN-17 lançamento usa a moeda base da carteira e data não futura | `Portfolio.record_transaction` | `test_portfolio_domain.py` |
| RN-18 não vender mais do que a posição detém | `Position.apply` (sell) | `test_portfolio_domain.py` |
| RN-19 custo médio ponderado na compra (taxas entram no custo); zerar posição zera o preço médio | `Position.apply` | `test_portfolio_domain.py` |
| RN-20 venda realiza ganho = resultado − custo médio × quantidade − taxas | `Position.apply` (sell) | `test_portfolio_domain.py` |
| RN-21 proventos somam em `income`, taxas em `costs`; resultado = realizado + proventos − taxas | `Position.net_result` | `test_portfolio_domain.py` |
| RN-22 carteira arquivada não aceita lançamentos nem alvos | `Portfolio._ensure_active` | `test_portfolio_domain.py` |
| RN-23 valoração marca a mercado; símbolo sem preço fica fora do valor e é reportado | `analytics/domain/valuation.py` (`valuate`) | `test_portfolio_domain.py` |
| RN-24 lista de carteiras é marcada a mercado em um único lote de cotações | `ListPortfolios` + `QuoteProvider.get_quotes` | `tests/api/test_portfolio_api.py` |

## Instrumentos e cotações (RM-01…RM-08)

| Regra | Implementação | Teste |
|---|---|---|
| RM-01 símbolo aceita padrão B3 (`PETR4`, `IGUATEMI11`) e símbolos gerais (`BTC-USD`, `^BVSP`) | `TickerSymbol` | `tests/unit/test_market_data_domain.py` |
| RM-02 ISIN com dígito verificador Luhn (ISO 6166) | `Isin` | `test_market_data_domain.py` |
| RM-03 MIC (ISO 10383) e CFI (ISO 10962) com formato validado | `Mic`, `CfiCode` | `test_market_data_domain.py` |
| RM-04 cotação exige timestamp UTC e preço não negativo | `Quote` | `test_market_data_domain.py` |
| RM-05 séries macro seguem o BCB: Selic/CDI diária, IPCA mensal, USD/BRL como nível | `SeedMacroProvider`, `BcbSgsProvider` | `test_market_data_router.py`, `tests/unit/test_market_data_providers.py` |
| RM-06 provider ao vivo nunca bloqueia: seed responde e cache é atualizado em background | `RoutedQuoteProvider`, `CachedMacroProvider` | `test_market_data_router.py` |
| RM-07 falha de provider não vira erro 500 (fallback determinístico + log) | `fetch_json`, providers | `test_market_data_providers.py` |
| RM-08 painel de mercado é resiliente: série/ativo indisponível é omitido | `GetMarketOverview` | `tests/unit/test_market_data_use_cases.py` |

## Performance e risco (RM-09…RM-15)

| Regra | Implementação | Teste |
|---|---|---|
| RM-09 TWR neutraliza aportes e retiradas (sub-períodos diários) | `analytics/domain/performance.py` (`time_weighted_return`) | `tests/unit/test_analytics_domain.py` |
| RM-10 XIRR por Newton-Raphson com fallback de bisseção, day count actual/365 | `money_weighted_return` | `test_analytics_domain.py` |
| RM-11 volatilidade anualizada em 252 dias; Sharpe usa Selic anualizada do BCB como livre de risco | `annualized_volatility`, `sharpe_ratio` | `test_analytics_domain.py` |
| RM-12 beta vs. Ibovespa, drawdown máximo e VaR histórico 95% | `beta`, `max_drawdown`, `historical_var` | `test_analytics_domain.py` |
| RM-13 drift em basis points contra o alvo; plano de rebalanceamento respeita valor mínimo | `analytics/domain/allocation.py` | `test_analytics_domain.py` |
| RM-14 série de patrimônio: posições × preço + caixa; aportes/vendas como fluxo externo, proventos internos | `analytics/application/valuation.py` | `test_analytics_domain.py` (ValuationPoint/TWR), `tests/api/test_market_api.py` |
| RM-15 taxa livre de risco nunca é extrapolada de janela longa (regressão do bug 8e14) | `CachedMacroProvider.latest` | `test_market_data_router.py` |

## Convenções transversais

- **Erros HTTP**: RFC 9457 (`application/problem+json`) com `code` estável e `X-Request-ID` — `kernel/infrastructure/http/errors.py`.
- **Paginação**: cursor opaco (keyset) em clientes, carteiras e instrumentos; instrumento do cursor assinado em base64url — `kernel/application/pagination.py`.
- **Dinheiro em JSON**: string exata + `numeric` (aproximação só para gráficos).
- **Fronteiras**: 8 contratos em `[tool.importlinter]` (`apps/api/pyproject.toml`).
- **i18n**: chaves estáveis no frontend com paridade PT/EN verificada por teste (`apps/web/src/shared/i18n/messages.test.ts`); a API nunca devolve texto traduzido.
- **Acessibilidade**: telas principais verificadas com axe-core nos testes de página.
