import { useId } from "react"
import { formatCurrency } from "../../lib/format"
import { cn } from "../../lib/utils"

export type DonutSlice = { label: string; value: number }

export type DonutProps = {
  data: DonutSlice[]
  size?: number
  thickness?: number
  currency?: string
  locale?: string
  className?: string
}

const INK_SHADES = [
  "var(--ink)",
  "color-mix(in srgb, var(--ink) 72%, var(--paper))",
  "color-mix(in srgb, var(--ink) 52%, var(--paper))",
  "color-mix(in srgb, var(--ink) 34%, var(--paper))",
  "color-mix(in srgb, var(--ink) 20%, var(--paper))",
  "var(--gold)",
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
  let offset = 0

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
          {slices.map((slice, index) => {
            const fraction = slice.value / total
            const dash = fraction * circumference
            const circle = (
              <circle
                key={slice.label}
                r={radius}
                fill="none"
                stroke={INK_SHADES[index % INK_SHADES.length]}
                strokeWidth={thickness}
                strokeDasharray={`${dash} ${circumference - dash}`}
                strokeDashoffset={-offset}
              />
            )
            offset += dash
            return circle
          })}
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
                style={{ background: INK_SHADES[index % INK_SHADES.length] }}
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
