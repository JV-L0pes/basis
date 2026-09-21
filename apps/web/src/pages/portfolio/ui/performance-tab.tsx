import type { components } from "@basis/contracts"
import { AreaChart, formatCurrency, Skeleton } from "@basis/ui"
import { useI18n } from "@/shared/i18n/provider"
import { percentOrDash, toneOf } from "@/shared/lib/display"
import { Metric } from "@/shared/ui/primitives"

type Performance = components["schemas"]["PerformanceResponse"]

const PERIODS = [
  { days: 90, key: "markets.period90" },
  { days: 180, key: "markets.period180" },
  { days: 365, key: "markets.period365" },
] as const

function PerformanceContent({ report }: { report: Performance }) {
  const { t, locale } = useI18n()
  return (
    <>
      <div className="panel">
        <div className="panel-head">
          <h3 className="text-base font-extrabold">{t("portfolios.equityCurve")}</h3>
          <span className="mono text-ash">
            {report.start} — {report.end}
          </span>
        </div>
        <div className="panel-body">
          <AreaChart
            data={report.equity_curve.map((point) => ({
              date: point.date,
              value: Number(point.value),
            }))}
            currency={report.currency}
            locale={locale}
          />
        </div>
      </div>

      <section className="metric-grid mt-6">
        <Metric
          label={t("portfolios.twr")}
          value={percentOrDash(report.twr, locale)}
          tone={toneOf(report.twr)}
        />
        <Metric
          label={t("portfolios.xirr")}
          value={percentOrDash(report.xirr, locale)}
          tone={toneOf(report.xirr)}
        />
        <Metric
          label={t("portfolios.volatility")}
          value={percentOrDash(report.volatility, locale)}
        />
        <Metric
          label={t("portfolios.sharpe")}
          value={report.sharpe === null ? "—" : report.sharpe.toFixed(2)}
        />
        <Metric
          label={t("portfolios.maxDrawdown")}
          value={percentOrDash(report.max_drawdown, locale)}
          tone="neg"
        />
        <Metric
          label={t("portfolios.beta")}
          value={report.beta === null ? "—" : report.beta.toFixed(2)}
        />
        <Metric label={t("portfolios.var")} value={percentOrDash(report.var_95, locale)} />
        <Metric
          label={t("portfolios.contributions")}
          value={formatCurrency(report.net_contributions, report.currency, locale)}
        />
      </section>
    </>
  )
}

export function PerformanceTab({
  report,
  isLoading,
  days,
  onDaysChange,
}: {
  report: Performance | undefined
  isLoading: boolean
  days: number
  onDaysChange: (days: number) => void
}) {
  const { t } = useI18n()

  return (
    <>
      <div className="mb-4 flex items-center gap-3">
        {PERIODS.map((period) => (
          <button
            key={period.days}
            type="button"
            className={days === period.days ? "pill h-9 px-4 text-xs" : "plain"}
            onClick={() => onDaysChange(period.days)}
          >
            {t(period.key)}
          </button>
        ))}
      </div>

      {isLoading ? <Skeleton className="h-72" /> : null}
      {!isLoading && report ? <PerformanceContent report={report} /> : null}
      {!isLoading && !report ? (
        <p className="mono text-ash">{t("common.insufficientData")}</p>
      ) : null}
    </>
  )
}
