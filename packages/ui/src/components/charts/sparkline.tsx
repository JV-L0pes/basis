import { useId } from "react"

import { cn } from "../../lib/utils"

export type SparklineProps = {
  data: number[]
  width?: number
  height?: number
  positive?: boolean
  className?: string
  strokeWidth?: number
}

/**
 * Pure SVG sparkline in the Ink language: hairline stroke over a faint area,
 * no axes, no library. Renders nothing for empty data.
 */
export function Sparkline({
  data,
  width = 120,
  height = 32,
  positive,
  className,
  strokeWidth = 1.5,
}: SparklineProps) {
  const gradientId = useId()
  const series = data.filter((value) => Number.isFinite(value))
  if (series.length < 2) return null

  const min = Math.min(...series)
  const max = Math.max(...series)
  const span = max - min || 1
  const stepX = width / (series.length - 1)

  const points = series.map((value, index) => {
    const x = index * stepX
    const y = height - ((value - min) / span) * height
    return `${x.toFixed(2)},${y.toFixed(2)}`
  })

  const first = series[0] ?? 0
  const last = series[series.length - 1] ?? 0
  const rising = positive ?? last >= first
  const colour = rising ? "var(--positive)" : "var(--negative)"
  const areaPath = `M0,${height} L${points.join(" L")} L${width},${height} Z`

  return (
    <svg
      className={cn("block overflow-visible", className)}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={rising ? "Trend de alta" : "Trend de baixa"}
      preserveAspectRatio="none"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={colour} stopOpacity="0.18" />
          <stop offset="100%" stopColor={colour} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#${gradientId})`} stroke="none" />
      <polyline
        points={points.join(" ")}
        fill="none"
        stroke={colour}
        strokeWidth={strokeWidth}
        strokeLinejoin="round"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  )
}
