import { AreaChart, Badge, formatCurrency, formatPercent, Skeleton, Sparkline } from "@basis/ui"
import { useParams } from "@tanstack/react-router"
import { useState } from "react"

import { useHistory, useInstrument, useQuote } from "@/entities/instrument/api"
import { useI18n } from "@/shared/i18n/provider"
import { Metric, PageHeader } from "@/shared/ui/primitives"

const PERIODS = [
  { days: 90, key: "markets.period90" },
  { days: 180, key: "markets.period180" },
  { days: 365, key: "markets.period365" },
] as const

export function InstrumentPage() {
  const { t, locale } = useI18n()
  const { symbol } = useParams({ from: "/mercado/$symbol" })
  const [days, setDays] = useState<number>(365)

  const instrument = useInstrument(symbol)
  const quote = useQuote(symbol)
  const history = useHistory(symbol, days)

  const points = history.data ?? []
  const closes = points.map((point) => Number(point.close))
  const change = quote.data?.change_percent ?? null

  return (
    <main className="shell page">
      {instrument.isLoading ? (
        <Skeleton className="h-12 w-72" />
      ) : (
        <PageHeader
          kicker={
            instrument.data
              ? t(`assetClass.${instrument.data.asset_class}` as "assetClass.equity")
              : t("markets.kicker")
          }
          title={instrument.data ? `${instrument.data.symbol} · ${instrument.data.name}` : symbol}
          subtitle={instrument.data?.isin ? `ISIN ${instrument.data.isin}` : undefined}
          actions={
            quote.data ? (
              <Badge variant={change !== null && change >= 0 ? "positive" : "negative"}>
                {quote.data.source} · {quote.data.as_of.slice(0, 10)}
              </Badge>
            ) : null
          }
        />
      )}

      <section className="metric-grid">
        <Metric
          label={t("markets.quote")}
          value={
            quote.data
              ? formatCurrency(quote.data.price, quote.data.currency, locale)
              : t("common.noData")
          }
        />
        <Metric
          label={t("markets.change")}
          value={change !== null ? formatPercent(change / 100, locale) : "—"}
          tone={change !== null ? (change >= 0 ? "pos" : "neg") : null}
        />
        <Metric
          label={t("markets.history")}
          value={`${points.length}`}
          delta={
            points.length > 1
              ? `${points[0]?.date} → ${points[points.length - 1]?.date}`
              : undefined
          }
        />
        <div className="metric">
          <span className="metric-label">{t("markets.change")}</span>
          <Sparkline data={closes} width={160} height={36} />
        </div>
      </section>

      <div className="flex items-center gap-3">
        {PERIODS.map((period) => (
          <button
            key={period.days}
            type="button"
            className={days === period.days ? "pill h-9 px-4 text-xs" : "plain"}
            onClick={() => setDays(period.days)}
          >
            {t(period.key)}
          </button>
        ))}
      </div>

      <div className="panel">
        <div className="panel-head">
          <h3 className="text-base font-extrabold">{t("markets.history")}</h3>
          <span className="mono text-ash">{t("markets.period")}</span>
        </div>
        <div className="panel-body">
          {history.isLoading ? (
            <Skeleton className="h-64" />
          ) : (
            <AreaChart
              data={points.map((point) => ({
                date: point.date,
                value: Number(point.close),
              }))}
              currency={points[0]?.currency ?? "BRL"}
              locale={locale}
            />
          )}
        </div>
      </div>
    </main>
  )
}
