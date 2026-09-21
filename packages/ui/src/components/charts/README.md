# Charts

Quatro gráficos na gramática Ink. Nenhum deles usa sombra, raio ou dourado
decorativo; gridlines e eixos são fios de 1px, rótulos em Martian Mono.

```tsx
import { AreaChart, CandleChart, Donut, Sparkline } from "@basis/ui/charts"
```

## `Sparkline`

```ts
{ data: number[]; width?: number; height?: number; positive?: boolean; className?: string; label?: string }
```

- SVG puro, sem biblioteca e sem tooltip.
- Traço de 1px em `currentColor` e área em `color-mix(in srgb, currentColor 10%, transparent)`.
- Tom automático: `positive` quando `último >= primeiro`, senão `negative`; pode ser forçado.
- Dados não finitos são ignorados. Lista vazia não renderiza nada; um único ponto vira uma regra plana.
- `label` vira `aria-label` (padrão `"Sparkline"`).

## `AreaChart`

```ts
{ data: { date: string; value: number }[]; height?: number; currency?: string; locale?: string; className?: string; label?: string }
```

- Série temporal em SVG puro; eixo Y com 5 gridlines e rótulos compactos via `Intl.NumberFormat`.
- Eixo X esparso: no máximo 5 datas (`formatDate` com dia + mês curto).
- Crosshair + tooltip no ponteiro; o SVG é focável e responde a `←` `→` `Home` `End` (e `Escape` limpa),
  com o valor ativo anunciado por `aria-live="polite"`.
- `currency` (padrão `BRL`) e `locale` alimentam `formatCurrency`; `height` (padrão 260) define a altura,
  a largura acompanha o container (ResizeObserver).
- Sem movimento obrigatório: a transição do tooltip é desligada com `prefers-reduced-motion`.

## `Donut`

```ts
{ data: { label: string; value: number }[]; size?: number; currency?: string; locale?: string; className?: string; label?: string }
```

- Setores anulares em SVG puro, cada um com contorno de 1px em `var(--ink)`.
- Total no centro em Martian Mono; legenda com rótulos `.mono` e números tabulares.
- Fatias com valor `<= 0` ou não finito são descartadas; sem dados (ou total zero) não renderiza nada.
- Uma única fatia usa `fill-rule="evenodd"` para fechar o anel sem arcos ambíguos.
- Escala de tons neutros (ink/ash em opacidades), nunca dourado.

## `CandleChart`

```ts
{ data: { time: string; open: number; high: number; low: number; close: number }[]; height?: number; className?: string; label?: string }
```

- Wrapper de `lightweight-charts` (TradingView) com o tema lido dos tokens CSS:
  fundo transparente, texto `--ash`, grid `--rule`, crosshair `--ink`, candles `positive` / `destructive`.
- `chart.remove()` no unmount e um `MutationObserver` em `data-theme` re-aplica as cores quando o tema troca.
- `time` aceita ISO (`2026-09-20`); os dados são reaplicados com `fitContent()` a cada mudança.
- Único gráfico que carrega biblioteca externa — importe-o só onde for necessário
  (`@basis/ui/charts` re-exporta todos, o bundler faz tree-shaking).
