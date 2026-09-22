# ADR 0004 — Dinheiro como Decimal de escala limitada

- Status: aceito
- Data: 2026-09-21
- Contexto: uma plataforma financeira que usa `float` para dinheiro acumula erro de representação. O legado misturava "valor investido" com "cotação" no mesmo campo numérico.

## Decisão

`Money` é um value object imutável (`Decimal` + `Currency`), com:

- rejeição de `float`, `NaN` e infinito na construção;
- escala máxima de 12 casas; multiplicação e divisão **arredondam para a escala do kernel** em vez de estourar (custo médio ponderado gera dízimas);
- arredondamento bancário (half-even) na menor unidade da moeda;
- `allocate` pelo método do maior resto — a soma dos rateios é exatamente o total;
- moedas ISO 4217 mais unidades cripto com expoente próprio (BTC 8, ETH 18, USDT 6).

No banco: `NUMERIC(28,10)`. No JSON: string exata + `numeric` apenas para gráficos.

## Consequências

- `Money(1.5, BRL)` falha: obriga o chamador a usar `Decimal`.
- Cálculos de carteira (custo médio, P&L, retorno) são exatos e reprodutíveis.
- O frontend nunca recalcula dinheiro: exibe o que a API enviou.
