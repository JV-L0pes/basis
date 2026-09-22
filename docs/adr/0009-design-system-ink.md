# ADR 0009 — Design system Ink compartilhado no monorepo

- Status: aceito
- Data: 2026-09-21
- Contexto: o autor já tinha uma linguagem visual própria ("Ink": tipografia Archivo/Martian Mono, radius 0, zero sombra, dourado racionado) usada no portfólio. Um produto financeiro com cara de template genérico jogaria fora o principal diferencial visual.

## Decisão

O Ink vira `packages/ui` (`@basis/ui`), consumido pelo app:

- tokens em CSS-first (`--paper`, `--ink`, `--ash`, `--rule`, `--gold`, `--chart-1..8`) com tema claro/escuro por `data-theme`;
- primitivos estilo shadcn sobre Radix (`button`, `input`, `select`, `dialog`, `dropdown`, `tabs`, `ledger`, `field`…), com `cva` para variantes;
- **gráficos próprios em SVG** (sparkline, área com crosshair por teclado, donut) — sem biblioteca — e `lightweight-charts` apenas para candles;
- paleta categórica para dados (`--chart-1..8`), mantendo o dourado reservado a sinal/valor.

## Consequências

- A UI não inventa cor: tudo vem de token; o ESLint/regras de estilo barram desvios grosseiros.
- O mesmo CSS pode ser reaproveitado em outros projetos do autor sem copiar componente.
- Custo: componentes próprios exigem testes (24 no pacote, incluindo axe nas telas).
