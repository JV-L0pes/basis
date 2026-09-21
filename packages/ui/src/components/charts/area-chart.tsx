import { useId, useMemo, useState } from "react"

import { formatCurrency, formatShortDate } from "../../lib/format"
import { cn } from "../../lib/utils"

export interface AreaChartPoint {
  date: string
  value: number
}

export interface AreaChartProps {
  data: AreaChartPoint[]
  height?: number
  currency?: string
  locale?: string
  className?: string
  /** Number of horizontal gridlines. */
  ticks?: number
}

const VIEW_WIDTH = 720
const PADDING = { top: 12, right: 8, bottom: 22, left: 56 }

/**
 * Time-series area chart in pure SVG: hairline gridlines, mono axis labels and
 * a crosshair driven by pointer movement or arrow keys (the chart itself is a
 * single focusable slider-like element, which keeps the accessibility tree
 * small even with hundreds of points).
 */
export function AreaChart({
  data,
  height = 240,
  currency = "BRL",
  locale = "pt-BR",
  className,
  ticks = 4,
}: AreaChartProps) {
  const gradientId = useId()
  const [active, setActive] = useState<number | null>(null)

  const series = useMemo(
    () =>
      data
        .map((point) => ({ date: point.date, value: point.value }))
        .filter((point) => Number.isFinite(point.value)),
    [data],
  )

  const innerWidth = VIEW_WIDTH - PADDING.left - PADDING.right
  const innerHeight = height - PADDING.top - PADDING.bottom

  if (series.length < 2) {
    return (
      <div
        className={cn("flex h-[160px] items-center justify-center border border-rule", className)}
      >
        <span className="mono text-ash">Dados insuficientes</span>
      </div>
    )
  }

  const values = series.map((point) => point.value)
  const first = values[0] ?? 0
  const last = values[values.length - 1] ?? 0
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const stepX = innerWidth / (series.length - 1)

  const x = (index: number) => PADDING.left + index * stepX
  const y = (value: number) => PADDING.top + innerHeight - ((value - min) / span) * innerHeight

  const line = series.map((point, index) => `${x(index).toFixed(2)},${y(point.value).toFixed(2)}`)
  const baseline = (PADDING.top + innerHeight).toFixed(2)
  const area = `M${x(0).toFixed(2)},${baseline} L${line.join(" L")} L${x(series.length - 1).toFixed(
    2,
  )},${baseline} Z`

  const gridValues = Array.from({ length: ticks + 1 }, (_, index) => min + (span * index) / ticks)
  const labelEvery = Math.max(1, Math.ceil(series.length / 6))
  const activeIndex = active !== null ? Math.min(Math.max(active, 0), series.length - 1) : null
  const activePoint = activeIndex !== null ? series[activeIndex] : undefined
  const rising = last >= first
  const colour = rising ? "var(--positive)" : "var(--negative)"

  const selectFromPointer = (event: React.MouseEvent<HTMLDivElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect()
    if (bounds.width === 0) return
    const relative = ((event.clientX - bounds.left) / bounds.width) * VIEW_WIDTH
    const index = Math.round((relative - PADDING.left) / stepX)
    setActive(Math.min(Math.max(index, 0), series.length - 1))
  }

  return (
    <div className={cn("relative", className)}>
      <div
        role="slider"
        tabIndex={0}
        aria-label={`Série temporal com ${series.length} pontos, de ${formatCurrency(
          first,
          currency,
          locale,
        )} a ${formatCurrency(last, currency, locale)}`}
        aria-valuemin={0}
        aria-valuemax={series.length - 1}
        aria-valuenow={activeIndex ?? series.length - 1}
        aria-valuetext={
          activePoint
            ? `${formatShortDate(activePoint.date, locale)}: ${formatCurrency(
                activePoint.value,
                currency,
                locale,
              )}`
            : undefined
        }
        onMouseMove={selectFromPointer}
        onMouseLeave={() => {
          setActive(null)
        }}
        onFocus={() => {
          setActive(activeIndex ?? series.length - 1)
        }}
        onBlur={() => {
          setActive(null)
        }}
        onKeyDown={(event) => {
          if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return
          event.preventDefault()
          const current = activeIndex ?? series.length - 1
          const next = event.key === "ArrowLeft" ? current - 1 : current + 1
          setActive(Math.min(Math.max(next, 0), series.length - 1))
        }}
      >
        <svg
          viewBox={`0 0 ${VIEW_WIDTH} ${height}`}
          width="100%"
          height={height}
          aria-hidden="true"
          focusable="false"
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={colour} stopOpacity="0.16" />
              <stop offset="100%" stopColor={colour} stopOpacity="0" />
            </linearGradient>
          </defs>

          {gridValues.map((value) => (
            <g key={value}>
              <line
                x1={PADDING.left}
                x2={VIEW_WIDTH - PADDING.right}
                y1={y(value)}
                y2={y(value)}
                stroke="var(--rule)"
                strokeWidth={1}
              />
              <text
                x={PADDING.left - 8}
                y={y(value) + 3}
                textAnchor="end"
                fontSize={9}
                fill="var(--ash)"
                fontFamily="var(--font-mono)"
              >
                {formatCurrency(value, currency, locale)}
              </text>
            </g>
          ))}

          <path d={area} fill={`url(#${gradientId})`} />
          <polyline
            points={line.join(" ")}
            fill="none"
            stroke="var(--ink)"
            strokeWidth={1.5}
            strokeLinejoin="round"
            vectorEffect="non-scaling-stroke"
          />

          {series.map((point, index) =>
            index % labelEvery === 0 || index === series.length - 1 ? (
              <text
                key={`${point.date}-label`}
                x={x(index)}
                y={height - 6}
                textAnchor="middle"
                fontSize={9}
                fill="var(--ash)"
                fontFamily="var(--font-mono)"
              >
                {formatShortDate(point.date, locale)}
              </text>
            ) : null,
          )}

          {activeIndex !== null ? (
            <g>
              <line
                x1={x(activeIndex)}
                x2={x(activeIndex)}
                y1={PADDING.top}
                y2={PADDING.top + innerHeight}
                stroke="var(--ink)"
                strokeWidth={1}
                strokeDasharray="2 3"
              />
              <circle
                cx={x(activeIndex)}
                cy={y(series[activeIndex]?.value ?? 0)}
                r={3}
                fill="var(--ink)"
              />
            </g>
          ) : null}
        </svg>
      </div>

      {activePoint && activeIndex !== null ? (
        <div
          className="pointer-events-none absolute top-0 border border-ink bg-paper px-2 py-1"
          style={{ left: `${(x(activeIndex) / VIEW_WIDTH) * 100}%` }}
        >
          <div className="mono text-[0.5rem] text-ash">
            {formatShortDate(activePoint.date, locale)}
          </div>
          <div className="font-numeric text-xs font-semibold">
            {formatCurrency(activePoint.value, currency, locale)}
          </div>
        </div>
      ) : null}
    </div>
  )
}
