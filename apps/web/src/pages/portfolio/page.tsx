import { Badge, Button, Skeleton, Tabs, TabsContent, TabsList, TabsTrigger } from "@basis/ui"
import { useParams } from "@tanstack/react-router"
import { useState } from "react"
import {
  useAllocation,
  usePerformance,
  usePortfolio,
  useTransactions,
} from "@/entities/portfolio/api"
import { RecordTransactionDialog } from "@/features/portfolios/record-transaction-dialog"
import { TargetAllocationDialog } from "@/features/portfolios/target-allocation-dialog"
import { useI18n } from "@/shared/i18n/provider"
import { currencyOrDash, percentPointsOrDash, toneOf } from "@/shared/lib/display"
import { Metric, PageHeader } from "@/shared/ui/primitives"
import { AllocationTab } from "./ui/allocation-tab"
import { LedgerTab } from "./ui/ledger-tab"
import { PerformanceTab } from "./ui/performance-tab"
import { PositionsTab } from "./ui/positions-tab"

export function PortfolioPage() {
  const { t, locale } = useI18n()
  const { portfolioId } = useParams({ from: "/carteiras/$portfolioId" })
  const [days, setDays] = useState<number>(365)
  const [txOpen, setTxOpen] = useState(false)
  const [targetsOpen, setTargetsOpen] = useState(false)

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
  const statusVariant = data.status === "active" ? "positive" : "muted"

  return (
    <main className="shell page">
      <PageHeader
        kicker={t("portfolios.kicker")}
        title={data.name}
        subtitle={`${data.base_currency} · ${data.position_count} ${t("portfolios.positions").toLowerCase()} · ${data.transaction_count} ${t("portfolios.transactions").toLowerCase()}`}
        actions={
          <>
            <Badge variant={statusVariant}>{t(`status.${data.status}` as "status.active")}</Badge>
            <Button variant="outline" onClick={() => setTargetsOpen(true)}>
              {t("portfolios.setTargets")}
            </Button>
            <Button onClick={() => setTxOpen(true)}>{t("portfolios.newTransaction")}</Button>
          </>
        }
      />

      <section className="metric-grid">
        <Metric
          label={t("portfolios.marketValue")}
          value={currencyOrDash(valuation?.market_value, data.base_currency, locale)}
        />
        <Metric
          label={t("portfolios.invested")}
          value={currencyOrDash(valuation?.invested, data.base_currency, locale)}
        />
        <Metric
          label={t("portfolios.netResult")}
          value={currencyOrDash(valuation?.net_result, data.base_currency, locale)}
          tone={toneOf(valuation?.net_result)}
        />
        <Metric
          label={t("portfolios.returnPercent")}
          value={percentPointsOrDash(valuation?.return_percent, locale)}
          tone={toneOf(valuation?.net_result)}
        />
        <Metric
          label={t("portfolios.income")}
          value={currencyOrDash(valuation?.income, data.base_currency, locale)}
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
          <PositionsTab
            positions={valuation?.positions ?? []}
            unpriced={valuation?.unpriced_symbols ?? []}
            baseCurrency={data.base_currency}
          />
        </TabsContent>

        <TabsContent value="ledger">
          <LedgerTab transactions={transactions.data ?? []} baseCurrency={data.base_currency} />
        </TabsContent>

        <TabsContent value="performance">
          <PerformanceTab
            report={performance.data}
            isLoading={performance.isLoading}
            days={days}
            onDaysChange={setDays}
          />
        </TabsContent>

        <TabsContent value="allocation">
          <AllocationTab analysis={allocation.data} />
        </TabsContent>
      </Tabs>

      <RecordTransactionDialog portfolioId={portfolioId} open={txOpen} onOpenChange={setTxOpen} />
      <TargetAllocationDialog
        portfolioId={portfolioId}
        targets={data.targets}
        open={targetsOpen}
        onOpenChange={setTargetsOpen}
      />
    </main>
  )
}
