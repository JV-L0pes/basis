import {
  CandlestickSeries,
  createChart,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts"
import { useEffect, useRef } from "react"

import { cn } from "../../lib/utils"

export interface Candle {
  time: string
  open: number
  high: number
  low: number
  close: number
}

export interface CandleChartProps {
  data: Candle[]
  height?: number
  className?: string
}

function token(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

/** TradingView lightweight-charts wrapper themed with the Ink palette. */
export function CandleChart({ data, height = 320, className }: CandleChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const chart = createChart(container, {
      height,
      layout: {
        background: { color: "transparent" },
        textColor: token("--ash", "#75736d"),
        fontFamily: token("--font-mono", "monospace"),
        fontSize: 10,
      },
      grid: {
        vertLines: { color: token("--rule", "#dfddd6") },
        horzLines: { color: token("--rule", "#dfddd6") },
      },
      rightPriceScale: { borderColor: token("--rule", "#dfddd6") },
      timeScale: { borderColor: token("--rule", "#dfddd6") },
      crosshair: {
        vertLine: { color: token("--ink", "#0d0d0c"), width: 1, style: 3 },
        horzLine: { color: token("--ink", "#0d0d0c"), width: 1, style: 3 },
      },
    })
    chartRef.current = chart

    const series = chart.addSeries(CandlestickSeries, {
      upColor: token("--positive", "#1f7a4d"),
      downColor: token("--negative", "#b3261e"),
      borderUpColor: token("--positive", "#1f7a4d"),
      borderDownColor: token("--negative", "#b3261e"),
      wickUpColor: token("--positive", "#1f7a4d"),
      wickDownColor: token("--negative", "#b3261e"),
    })

    series.setData(
      data.map((candle) => ({
        time: (Date.parse(candle.time) / 1000) as UTCTimestamp,
        open: candle.open,
        high: candle.high,
        low: candle.low,
        close: candle.close,
      })),
    )
    chart.timeScale().fitContent()

    const observer = new MutationObserver(() => {
      chart.applyOptions({
        layout: { textColor: token("--ash", "#75736d") },
        grid: {
          vertLines: { color: token("--rule", "#dfddd6") },
          horzLines: { color: token("--rule", "#dfddd6") },
        },
      })
    })
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    })

    return () => {
      observer.disconnect()
      chart.remove()
      chartRef.current = null
    }
  }, [data, height])

  return <div ref={containerRef} className={cn("w-full", className)} style={{ height }} />
}
