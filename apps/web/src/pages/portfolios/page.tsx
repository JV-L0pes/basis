import {
  Badge,
  Button,
  formatCurrency,
  Ledger,
  LedgerBody,
  LedgerCell,
  LedgerHead,
  LedgerHeadCell,
  LedgerRow,
  Skeleton,
} from "@basis/ui"
import { Link, useSearch } from "@tanstack/react-router"
import { useState } from "react"

import { useBookOverview } from "@/entities/instrument/api"
import { usePortfolios } from "@/entities/portfolio/api"
import { OpenPortfolioDialog } from "@/features/portfolios/open-portfolio-dialog"
import { useI18n } from "@/shared/i18n/provider"
import { currencyOrDash, percentPointsOrDash, toneOf } from "@/shared/lib/display"
import { Metric, PageHeader } from "@/shared/ui/primitives"

const SKELETON_KEYS = ["r1", "r2", "r3", "r4", "r5"] as const

export function PortfoliosPage() {
  const { t, locale } = useI18n()
  const { clientId } = useSearch({ from: "/carteiras" })
  const portfolios = usePortfolios({ clientId })
  const book = useBookOverview()
  const [dialogOpen, setDialogOpen] = useState(false)

  const items = portfolios.data?.items ?? []
  const totalResult = items.reduce(
    (sum, portfolio) => sum + Number(portfolio.valuation?.net_result ?? 0),
    0,
  )

  return (
    <main className="shell page">
      <PageHeader
        kicker={t("portfolios.kicker")}
        title={t("portfolios.title")}
        subtitle={t("portfolios.subtitle")}
        actions={<Button onClick={() => setDialogOpen(true)}>{t("portfolios.new")}</Button>}
      />

      <section className="metric-grid">
        <Metric
          label={t("dashboard.aum")}
          value={currencyOrDash(book.data?.total_market_value, "BRL", locale)}
        />
        <Metric label={t("dashboard.portfolios")} value={String(book.data?.portfolio_count ?? 0)} />
        <Metric
          label={t("portfolios.netResult")}
          value={formatCurrency(totalResult, "BRL", locale)}
          tone={toneOf(totalResult)}
        />
      </section>

      {portfolios.isLoading ? (
        <div className="flex flex-col gap-2">
          {SKELETON_KEYS.map((key) => (
            <Skeleton key={key} />
          ))}
        </div>
      ) : (
        <Ledger>
          <LedgerHead>
            <LedgerRow>
              <LedgerHeadCell>{t("portfolios.name")}</LedgerHeadCell>
              <LedgerHeadCell>{t("portfolios.positions")}</LedgerHeadCell>
              <LedgerHeadCell numeric>{t("portfolios.marketValue")}</LedgerHeadCell>
              <LedgerHeadCell numeric>{t("portfolios.netResult")}</LedgerHeadCell>
              <LedgerHeadCell numeric>{t("portfolios.returnPercent")}</LedgerHeadCell>
              <LedgerHeadCell>—</LedgerHeadCell>
            </LedgerRow>
          </LedgerHead>
          <LedgerBody>
            {items.map((portfolio) => {
              const valuation = portfolio.valuation
              const statusVariant = portfolio.status === "active" ? "positive" : "muted"
              return (
                <LedgerRow key={portfolio.id}>
                  <LedgerCell>
                    <Link
                      to="/carteiras/$portfolioId"
                      params={{ portfolioId: portfolio.id }}
                      className="link font-semibold"
                    >
                      {portfolio.name}
                    </Link>
                    <div className="mono text-ash">{portfolio.base_currency}</div>
                  </LedgerCell>
                  <LedgerCell>
                    <span className="mono text-ash">
                      {portfolio.position_count} · {portfolio.transaction_count} lanç.
                    </span>
                  </LedgerCell>
                  <LedgerCell numeric>
                    {currencyOrDash(valuation?.market_value, portfolio.base_currency, locale)}
                  </LedgerCell>
                  <LedgerCell numeric className={toneOf(valuation?.net_result) ?? ""}>
                    {currencyOrDash(valuation?.net_result, portfolio.base_currency, locale)}
                  </LedgerCell>
                  <LedgerCell numeric>
                    {percentPointsOrDash(valuation?.return_percent, locale)}
                  </LedgerCell>
                  <LedgerCell numeric>
                    <Badge variant={statusVariant}>
                      {t(`status.${portfolio.status}` as "status.active")}
                    </Badge>
                  </LedgerCell>
                </LedgerRow>
              )
            })}
          </LedgerBody>
        </Ledger>
      )}

      <OpenPortfolioDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </main>
  )
}
