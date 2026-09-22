import { useId } from "react"

import { formatCurrency } from "../../lib/format"
import { cn } from "../../lib/utils"

export interface DonutSlice {
  label: string
  value: number
}

export interface DonutProps {
  data: DonutSlice[]
  size?: number
  thickness?: number
  currency?: string
  locale?: string
  className?: string
}

const CHART_COLOURS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "var(--chart-6)",
  "var(--chart-7)",
  "var(--chart-8)",
]

/** Allocation donut in pure SVG with an ink hairline between slices. */
export function Donut({
  data,
  size = 220,
  thickness = 26,
  currency = "BRL",
  locale = "pt-BR",
  className,
}: DonutProps) {
  const titleId = useId()
  const slices = data.filter((slice) => Number.isFinite(slice.value) && slice.value > 0)
  const total = slices.reduce((sum, slice) => sum + slice.value, 0)

  if (slices.length === 0 || total <= 0) {
    return (
      <div
        className={cn("flex items-center justify-center border border-rule", className)}
        style={{ width: size, height: size }}
      >
        <span className="mono text-ash">Sem posições</span>
      </div>
    )
  }

  const radius = (size - thickness) / 2
  const circumference = 2 * Math.PI * radius

  // Prefix sums keep the arc computation pure (no mutation during render).
  const arcs = slices.map((slice, index) => {
    const startFraction = slices.slice(0, index).reduce((sum, item) => sum + item.value, 0) / total
    return {
      slice,
      dash: (slice.value / total) * circumference,
      offset: startFraction * circumference,
      colour: CHART_COLOURS[index % CHART_COLOURS.length],
    }
  })

  return (
    <div className={cn("flex items-center gap-6", className)}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        aria-labelledby={titleId}
      >
        <title id={titleId}>Alocação por classe de ativo</title>
        <g transform={`translate(${size / 2}, ${size / 2}) rotate(-90)`}>
          {arcs.map((arc) => (
            <circle
              key={arc.slice.label}
              r={radius}
              fill="none"
              stroke={arc.colour}
              strokeWidth={thickness}
              strokeDasharray={`${arc.dash} ${circumference - arc.dash}`}
              strokeDashoffset={-arc.offset}
            />
          ))}
        </g>
        <text
          x="50%"
          y="47%"
          textAnchor="middle"
          fontSize={10}
          fill="var(--ash)"
          fontFamily="var(--font-mono)"
          letterSpacing="0.14em"
        >
          TOTAL
        </text>
        <text x="50%" y="56%" textAnchor="middle" fontSize={13} fontWeight={700} fill="var(--ink)">
          {formatCurrency(total, currency, locale)}
        </text>
      </svg>

      <ul className="flex min-w-0 flex-1 flex-col gap-2">
        {slices.map((slice, index) => (
          <li
            key={slice.label}
            className="flex items-baseline justify-between gap-3 border-b border-rule pb-1"
          >
            <span className="flex min-w-0 items-center gap-2">
              <span
                aria-hidden="true"
                className="inline-block h-2.5 w-2.5 flex-none"
                style={{ background: CHART_COLOURS[index % CHART_COLOURS.length] }}
              />
              <span className="mono truncate text-[0.55rem] text-ash">{slice.label}</span>
            </span>
            <span className="tnum font-numeric text-xs whitespace-nowrap">
              {((slice.value / total) * 100).toFixed(1)}%
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
