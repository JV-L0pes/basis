import {
  Badge,
  Button,
  formatCurrency,
  formatPercent,
  Ledger,
  LedgerBody,
  LedgerCell,
  LedgerHead,
  LedgerHeadCell,
  LedgerRow,
  Skeleton,
} from "@basis/ui"
import { useState } from "react"
import { useBookOverview } from "@/entities/instrument/api"
import { usePortfolios } from "@/entities/portfolio/api"
import { OpenPortfolioDialog } from "@/features/portfolios/open-portfolio-dialog"
import { useI18n } from "@/shared/i18n/provider"
import { Metric, PageHeader } from "@/shared/ui/primitives"

export function PortfoliosPage() {
  const { t, locale } = useI18n()
  const portfolios = usePortfolios()
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
          value={formatCurrency(book.data?.total_market_value ?? 0, "BRL", locale)}
        />
        <Metric label={t("dashboard.portfolios")} value={String(book.data?.portfolio_count ?? 0)} />
        <Metric
          label={t("portfolios.netResult")}
          value={formatCurrency(totalResult, "BRL", locale)}
          tone={totalResult >= 0 ? "pos" : "neg"}
        />
      </section>

      {portfolios.isLoading ? (
        <div className="flex flex-col gap-2">
          {["r1", "r2", "r3", "r4", "r5"].map((key) => (
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
              const result = Number(valuation?.net_result ?? 0)
              return (
                <LedgerRow key={portfolio.id}>
                  <LedgerCell>
                    <a className="link font-semibold" href={`/carteiras/${portfolio.id}`}>
                      {portfolio.name}
                    </a>
                    <div className="mono text-ash">{portfolio.base_currency}</div>
                  </LedgerCell>
                  <LedgerCell>
                    <span className="mono text-ash">
                      {portfolio.position_count} · {portfolio.transaction_count} lanç.
                    </span>
                  </LedgerCell>
                  <LedgerCell numeric>
                    {formatCurrency(valuation?.market_value ?? 0, portfolio.base_currency, locale)}
                  </LedgerCell>
                  <LedgerCell numeric className={result >= 0 ? "pos" : "neg"}>
                    {formatCurrency(result, portfolio.base_currency, locale)}
                  </LedgerCell>
                  <LedgerCell numeric>
                    {valuation?.return_percent !== null && valuation?.return_percent !== undefined
                      ? formatPercent(Number(valuation.return_percent) / 100, locale)
                      : "—"}
                  </LedgerCell>
                  <LedgerCell numeric>
                    <Badge variant={portfolio.status === "active" ? "positive" : "muted"}>
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
