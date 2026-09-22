# ADR 0006 — Performance e risco como calculadoras puras

- Status: aceito
- Data: 2026-09-21
- Contexto: TWR, XIRR e métricas de risco são fáceis de implementar errado e difíceis de auditar quando estão embutidas em consultas SQL ou em componentes de tela.

## Decisão

A matemática financeira vive em `analytics/domain/performance.py` e `analytics/domain/allocation.py` como funções puras: recebem séries e devolvem números, sem banco, rede ou framework. Convenções documentadas no próprio módulo:

- retornos são frações decimais; ano de 252 dias úteis para anualização;
- **TWR** por sub-períodos diários, neutralizando aportes e retiradas;
- **XIRR** por Newton-Raphson com fallback de bisseção, day count actual/365;
- volatilidade, Sharpe (com Selic anualizada do BCB como taxa livre de risco), beta vs. Ibovespa, drawdown máximo e VaR histórico 95%;
- alocação: exposição por classe, drift em basis points e plano de rebalanceamento com *trade* mínimo.

A projeção que transforma o extrato em série de patrimônio é um read model do contexto (`application/valuation.py`), com premissas explícitas: aportes entram como fluxo externo, vendas saem, proventos e taxas permanecem como caixa, ativos sem preço são marcados pelo custo.

## Consequências

- Testes com vetores conhecidos (ex.: −1000 hoje, +1100 em 365 dias ⇒ 10% a.a.) rodam em milissegundos.
- Trocar a fonte dos dados não muda a matemática; trocar a matemática não muda a API.
- Limitação assumida: sem conta corrente modelada, o caixa é tratado como reinvestido.
