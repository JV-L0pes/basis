import {
  AreaChart,
  Badge,
  Button,
  Donut,
  formatBasisPoints,
  formatCurrency,
  formatDate,
  formatPercent,
  Ledger,
  LedgerBody,
  LedgerCell,
  LedgerHead,
  LedgerHeadCell,
  LedgerRow,
  Skeleton,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@basis/ui"
import { useParams } from "@tanstack/react-router"
import { useState } from "react"

import {
  useAllocation,
  usePerformance,
  usePortfolio,
  useTransactions,
} from "@/entities/portfolio/api"
import { RecordTransactionDialog } from "@/features/portfolios/record-transaction-dialog"
import { useI18n } from "@/shared/i18n/provider"
import { Metric, PageHeader } from "@/shared/ui/primitives"

const PERIODS = [
  { days: 90, key: "markets.period90" },
  { days: 180, key: "markets.period180" },
  { days: 365, key: "markets.period365" },
] as const

export function PortfolioPage() {
  const { t, locale } = useI18n()
  const { portfolioId } = useParams({ from: "/carteiras/$portfolioId" })
  const [days, setDays] = useState<number>(365)
  const [txOpen, setTxOpen] = useState(false)

  const portfolio = usePortfolio(portfolioId)
  const transactions = useTransactions(portfolioId)
  const performance = usePerformance(portfolioId, days)
  const allocation = useAllocation(portfolioId)

  if (portfolio.isLoading) {
    return (
      <main className="shell page">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-24" />
        <Skeleton className="h-72" />
      </main>
    )
  }

  if (portfolio.error || !portfolio.data) {
    return (
      <main className="shell page">
        <PageHeader kicker="404" title={t("common.error")} subtitle={t("common.emptyHint")} />
      </main>
    )
  }

  const data = portfolio.data
  const valuation = data.valuation
  const report = performance.data
  const analysis = allocation.data
  const result = Number(valuation?.net_result ?? 0)

  return (
    <main className="shell page">
      <PageHeader
        kicker={t("portfolios.kicker")}
        title={data.name}
        subtitle={`${data.base_currency} · ${data.position_count} ${t("portfolios.positions").toLowerCase()} · ${data.transaction_count} ${t("portfolios.transactions").toLowerCase()}`}
        actions={
          <>
            <Badge variant={data.status === "active" ? "positive" : "muted"}>
              {t(`status.${data.status}` as "status.active")}
            </Badge>
            <Button onClick={() => setTxOpen(true)}>{t("portfolios.newTransaction")}</Button>
          </>
        }
      />

      <section className="metric-grid">
        <Metric
          label={t("portfolios.marketValue")}
          value={formatCurrency(valuation?.market_value ?? 0, data.base_currency, locale)}
        />
        <Metric
          label={t("portfolios.invested")}
          value={formatCurrency(valuation?.invested ?? 0, data.base_currency, locale)}
        />
        <Metric
          label={t("portfolios.netResult")}
          value={formatCurrency(result, data.base_currency, locale)}
          tone={result >= 0 ? "pos" : "neg"}
        />
        <Metric
          label={t("portfolios.returnPercent")}
          value={
            valuation?.return_percent !== null && valuation?.return_percent !== undefined
              ? formatPercent(Number(valuation.return_percent) / 100, locale)
              : "—"
          }
          tone={result >= 0 ? "pos" : "neg"}
        />
        <Metric
          label={t("portfolios.income")}
          value={formatCurrency(valuation?.income ?? 0, data.base_currency, locale)}
        />
      </section>

      <Tabs defaultValue="positions">
        <TabsList>
          <TabsTrigger value="positions">{t("portfolios.positions")}</TabsTrigger>
          <TabsTrigger value="ledger">{t("portfolios.transactions")}</TabsTrigger>
          <TabsTrigger value="performance">{t("portfolios.performance")}</TabsTrigger>
          <TabsTrigger value="allocation">{t("portfolios.allocation")}</TabsTrigger>
        </TabsList>

        <TabsContent value="positions">
          <Ledger>
            <LedgerHead>
              <LedgerRow>
                <LedgerHeadCell>{t("common.symbol")}</LedgerHeadCell>
                <LedgerHeadCell numeric>{t("common.quantity")}</LedgerHeadCell>
                <LedgerHeadCell numeric>{t("portfolios.averageCost")}</LedgerHeadCell>
                <LedgerHeadCell numeric>{t("portfolios.costBasis")}</LedgerHeadCell>
                <LedgerHeadCell numeric>{t("portfolios.marketValue")}</LedgerHeadCell>
                <LedgerHeadCell numeric>{t("portfolios.unrealized")}</LedgerHeadCell>
                <LedgerHeadCell numeric>{t("common.weight")}</LedgerHeadCell>
              </LedgerRow>
            </LedgerHead>
            <LedgerBody>
              {(valuation?.positions ?? []).map((position) => {
                const gain = Number(position.unrealized_gain ?? 0)
                return (
                  <LedgerRow key={position.symbol}>
                    <LedgerCell>
                      <a className="link" href={`/mercado/${position.symbol}`}>
                        {position.symbol}
                      </a>
                      <div className="mono text-ash">
                        {t(`assetClass.${position.asset_class}` as "assetClass.equity")}
                      </div>
                    </LedgerCell>
                    <LedgerCell numeric>{position.quantity}</LedgerCell>
                    <LedgerCell numeric>
                      {formatCurrency(position.average_cost, position.currency, locale)}
                    </LedgerCell>
                    <LedgerCell numeric>
                      {formatCurrency(position.cost_basis, position.currency, locale)}
                    </LedgerCell>
                    <LedgerCell numeric>
                      {position.market_value
                        ? formatCurrency(position.market_value, position.currency, locale)
                        : t("portfolios.unpriced")}
                    </LedgerCell>
                    <LedgerCell numeric className={gain >= 0 ? "pos" : "neg"}>
                      {position.unrealized_gain
                        ? formatCurrency(gain, position.currency, locale)
                        : "—"}
                    </LedgerCell>
                    <LedgerCell numeric>
                      {position.weight !== null && position.weight !== undefined
                        ? formatPercent(position.weight, locale, 1)
                        : "—"}
                    </LedgerCell>
                  </LedgerRow>
                )
              })}
            </LedgerBody>
          </Ledger>
          {valuation?.unpriced_symbols.length ? (
            <p className="mono mt-3 text-ash">
              {t("portfolios.unpriced")}: {valuation.unpriced_symbols.join(", ")}
            </p>
          ) : null}
        </TabsContent>

        <TabsContent value="ledger">
          <Ledger>
            <LedgerHead>
              <LedgerRow>
                <LedgerHeadCell>{t("common.date")}</LedgerHeadCell>
                <LedgerHeadCell>{t("common.type")}</LedgerHeadCell>
                <LedgerHeadCell>{t("common.symbol")}</LedgerHeadCell>
                <LedgerHeadCell numeric>{t("common.quantity")}</LedgerHeadCell>
                <LedgerHeadCell numeric>{t("common.price")}</LedgerHeadCell>
                <LedgerHeadCell numeric>{t("common.total")}</LedgerHeadCell>
              </LedgerRow>
            </LedgerHead>
            <LedgerBody>
              {(transactions.data ?? []).map((transaction) => (
                <LedgerRow key={transaction.id}>
                  <LedgerCell>{formatDate(transaction.trade_date, locale)}</LedgerCell>
                  <LedgerCell>
                    <Badge
                      variant={
                        transaction.kind === "buy"
                          ? "neutral"
                          : transaction.kind === "sell"
                            ? "gold"
                            : "muted"
                      }
                    >
                      {t(`transactionKind.${transaction.kind}` as "transactionKind.buy")}
                    </Badge>
                  </LedgerCell>
                  <LedgerCell>{transaction.symbol}</LedgerCell>
                  <LedgerCell numeric>{transaction.quantity}</LedgerCell>
                  <LedgerCell numeric>
                    {formatCurrency(transaction.price, data.base_currency, locale)}
                  </LedgerCell>
                  <LedgerCell numeric>
                    {formatCurrency(transaction.gross_value, data.base_currency, locale)}
                  </LedgerCell>
                </LedgerRow>
              ))}
            </LedgerBody>
          </Ledger>
        </TabsContent>

        <TabsContent value="performance">
          <div className="mb-4 flex items-center gap-3">
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

          {performance.isLoading ? (
            <Skeleton className="h-72" />
          ) : report ? (
            <>
              <div className="panel">
                <div className="panel-head">
                  <h3 className="text-base font-extrabold">{t("portfolios.equityCurve")}</h3>
                  <span className="mono text-ash">
                    {formatDate(report.start, locale)} — {formatDate(report.end, locale)}
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
                  value={report.twr !== null ? formatPercent(report.twr, locale) : "—"}
                  tone={report.twr !== null ? (report.twr >= 0 ? "pos" : "neg") : null}
                />
                <Metric
                  label={t("portfolios.xirr")}
                  value={report.xirr !== null ? formatPercent(report.xirr, locale) : "—"}
                  tone={report.xirr !== null ? (report.xirr >= 0 ? "pos" : "neg") : null}
                />
                <Metric
                  label={t("portfolios.volatility")}
                  value={
                    report.volatility !== null ? formatPercent(report.volatility, locale) : "—"
                  }
                />
                <Metric
                  label={t("portfolios.sharpe")}
                  value={report.sharpe !== null ? report.sharpe.toFixed(2) : "—"}
                />
                <Metric
                  label={t("portfolios.maxDrawdown")}
                  value={formatPercent(report.max_drawdown, locale)}
                  tone="neg"
                />
                <Metric
                  label={t("portfolios.beta")}
                  value={report.beta !== null ? report.beta.toFixed(2) : "—"}
                />
                <Metric
                  label={t("portfolios.var")}
                  value={report.var_95 !== null ? formatPercent(report.var_95, locale) : "—"}
                />
                <Metric
                  label={t("portfolios.contributions")}
                  value={formatCurrency(report.net_contributions, report.currency, locale)}
                />
              </section>
            </>
          ) : (
            <p className="mono text-ash">{t("common.insufficientData")}</p>
          )}
        </TabsContent>

        <TabsContent value="allocation">
          {analysis ? (
            <div className="panel-grid two">
              <div className="panel">
                <div className="panel-head">
                  <h3 className="text-base font-extrabold">{t("portfolios.allocation")}</h3>
                  <span className="mono text-ash">
                    {formatCurrency(analysis.total_value, analysis.currency, locale)}
                  </span>
                </div>
                <div className="panel-body">
                  <Donut
                    data={analysis.exposures.map((exposure) => ({
                      label: t(`assetClass.${exposure.asset_class}` as "assetClass.equity"),
                      value: Number(exposure.value),
                    }))}
                    currency={analysis.currency}
                    locale={locale}
                  />
                </div>
              </div>

              <div className="panel">
                <div className="panel-head">
                  <h3 className="text-base font-extrabold">{t("portfolios.plan")}</h3>
                  <span className="mono text-ash">{t("portfolios.drift")}</span>
                </div>
                <AsyncAllocation analysis={analysis} />
              </div>
            </div>
          ) : (
            <Skeleton className="h-64" />
          )}
        </TabsContent>
      </Tabs>

      <RecordTransactionDialog portfolioId={portfolioId} open={txOpen} onOpenChange={setTxOpen} />
    </main>
  )
}

function AsyncAllocation({
  analysis,
}: {
  analysis: NonNullable<ReturnType<typeof useAllocation>["data"]>
}) {
  const { t, locale } = useI18n()
  if (!analysis.has_targets) {
    return <div className="panel-body mono text-ash">{t("portfolios.noTargets")}</div>
  }
  return (
    <div className="panel-body">
      <Ledger>
        <LedgerHead>
          <LedgerRow>
            <LedgerHeadCell>{t("markets.filterClass")}</LedgerHeadCell>
            <LedgerHeadCell numeric>{t("portfolios.allocation")}</LedgerHeadCell>
            <LedgerHeadCell numeric>{t("portfolios.targets")}</LedgerHeadCell>
            <LedgerHeadCell numeric>{t("portfolios.drift")}</LedgerHeadCell>
            <LedgerHeadCell>—</LedgerHeadCell>
          </LedgerRow>
        </LedgerHead>
        <LedgerBody>
          {analysis.drift.map((item) => (
            <LedgerRow key={item.asset_class}>
              <LedgerCell>{t(`assetClass.${item.asset_class}` as "assetClass.equity")}</LedgerCell>
              <LedgerCell numeric>{formatPercent(item.current_weight, locale, 1)}</LedgerCell>
              <LedgerCell numeric>{formatPercent(item.target_weight, locale, 1)}</LedgerCell>
              <LedgerCell numeric className={item.drift_bps >= 0 ? "pos" : "neg"}>
                {formatBasisPoints(item.drift_bps, locale)}
              </LedgerCell>
              <LedgerCell numeric>
                {item.delta_value !== "0.00"
                  ? `${item.delta_value} ${analysis.currency}`
                  : t("portfolios.hold")}
              </LedgerCell>
            </LedgerRow>
          ))}
        </LedgerBody>
      </Ledger>
    </div>
  )
}
