# Charts

Quatro gráficos na gramática Ink — sem sombra, sem raio, sem dourado decorativo. Eixos e
gridlines são fios de 1px, rótulos em Martian Mono e a paleta categórica (`--chart-1..8`)
aparece apenas onde cor é informação.

```tsx
import { AreaChart, CandleChart, Donut, Sparkline } from "@basis/ui/charts"
```

## `Sparkline`

```ts
{ data: number[]; width?: number; height?: number; positive?: boolean; className?: string; strokeWidth?: number }
```

- SVG puro, sem biblioteca: uma `polyline` sobre uma área com gradiente do próprio tom.
- Tom automático: verde quando o último valor ≥ o primeiro, vermelho caso contrário; `positive` força.
- Ignora valores não finitos; com menos de dois pontos não renderiza nada (um ponto não é tendência).
- Largura/altura padrão: 120×32.

## `AreaChart`

```ts
{ data: { date: string; value: number }[]; height?: number; currency?: string; locale?: string; className?: string; ticks?: number }
```

- Série temporal em SVG puro, `viewBox` fixo e largura fluida pelo container.
- Gridlines de 1px com rótulos em `formatCurrency`; eixo X esparso via `formatShortDate`.
- A área é um `role="slider"` focável: `←`/`→` movem o crosshair, o ponteiro também, e
  `aria-valuetext` anuncia data e valor (`aria-valuenow` = índice).
- Sem dados suficientes (< 2 pontos) mostra um aviso em vez de um gráfico vazio.
- Tom da linha/área segue a tendência do período (verde/vermelho).

## `Donut`

```ts
{ data: { label: string; value: number }[]; size?: number; thickness?: number; currency?: string; locale?: string; className?: string }
```

- Setores em SVG puro com a **paleta categórica** `--chart-1..8` (definida em tokens, com
  variante clara e escura), separados pelo próprio recorte anular.
- Total no centro em Martian Mono; legenda com amostra de cor, rótulo mono e percentual tabular.
- Fatias com valor ≤ 0 ou não finito são descartadas; sem dados mostra "Sem posições".
- Offsets calculados por soma de prefixo (render puro, sem mutação durante o render).

## `CandleChart`

```ts
{ data: { time: string; open: number; high: number; low: number; close: number }[]; height?: number; className?: string }
```

- Wrapper de `lightweight-charts` (TradingView) com as cores lidas dos tokens CSS:
  fundo transparente, texto `--ash`, grid `--rule`, crosshair `--ink`, candles
  `--positive`/`--negative`.
- `chart.remove()` no unmount e um `MutationObserver` em `data-theme` re-aplica as cores
  quando o tema troca.
- Único gráfico que carrega biblioteca externa — importe-o só onde for necessário.
- Não é usado na UI atual (a API entrega fechamentos diários, não OHLC); fica pronto para
  quando houver candles de verdade.
