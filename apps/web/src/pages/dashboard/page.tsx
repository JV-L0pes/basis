import {
  cn,
  Donut,
  formatCompact,
  formatCurrency,
  Ledger,
  LedgerBody,
  LedgerCell,
  LedgerHead,
  LedgerHeadCell,
  LedgerRow,
  Sparkline,
} from "@basis/ui"
import { TrendDown, TrendUp } from "@basis/ui/icons"
import { Link } from "@tanstack/react-router"

import { useBookOverview, useMarketOverview } from "@/entities/instrument/api"
import { usePortfolios } from "@/entities/portfolio/api"
import { useI18n } from "@/shared/i18n/provider"
import { currencyOrDash, percentPointsOrDash, toneOf } from "@/shared/lib/display"
import { AsyncState, Metric, PageHeader } from "@/shared/ui/primitives"
import { MarketTicker } from "@/widgets/market-ticker/market-ticker"

const MACRO_LABELS: Record<string, string> = {
  selic: "Selic",
  cdi: "CDI",
  ipca: "IPCA",
  usd_brl: "USD/BRL",
}

function AllocationPanel() {
  const { t, locale } = useI18n()
  const book = useBookOverview()

  return (
    <div className="panel">
      <div className="panel-head">
        <h3 className="text-base font-extrabold">{t("dashboard.bookAllocation")}</h3>
        <span className="mono text-ash">
          {formatCompact(book.data?.portfolio_count ?? 0, locale)} {t("dashboard.portfolios")}
        </span>
      </div>
      <div className="panel-body">
        <AsyncState
          isLoading={book.isLoading}
          error={book.error}
          isEmpty={(book.data?.allocation.length ?? 0) === 0}
          emptyLabel={t("common.empty")}
        >
          <Donut
            data={(book.data?.allocation ?? []).map((item) => ({
              label: t(`assetClass.${item.asset_class}` as "assetClass.equity"),
              value: Number(item.value),
            }))}
            currency="BRL"
            locale={locale}
          />
        </AsyncState>
      </div>
    </div>
  )
}

function TopPortfoliosPanel({ className }: { className?: string }) {
  const { t, locale } = useI18n()
  const portfolios = usePortfolios()
  const top = [...(portfolios.data?.items ?? [])].sort(
    (a, b) => Number(b.valuation?.market_value ?? 0) - Number(a.valuation?.market_value ?? 0),
  )

  return (
    <div className={cn("panel flex flex-col", className)}>
      <div className="panel-head">
        <h3 className="text-base font-extrabold">{t("dashboard.topClients")}</h3>
        <Link to="/carteiras" className="plain mono">
          {t("portfolios.title")}
        </Link>
      </div>
      <AsyncState
        isLoading={portfolios.isLoading}
        error={portfolios.error}
        isEmpty={top.length === 0}
        emptyLabel={t("portfolios.empty")}
      >
        <Ledger>
          <LedgerHead>
            <LedgerRow>
              <LedgerHeadCell>{t("portfolios.name")}</LedgerHeadCell>
              <LedgerHeadCell numeric>{t("portfolios.marketValue")}</LedgerHeadCell>
              <LedgerHeadCell numeric>{t("portfolios.netResult")}</LedgerHeadCell>
              <LedgerHeadCell numeric>{t("portfolios.returnPercent")}</LedgerHeadCell>
              <LedgerHeadCell>—</LedgerHeadCell>
            </LedgerRow>
          </LedgerHead>
          <LedgerBody>
            {top.map((portfolio) => {
              const valuation = portfolio.valuation
              return (
                <LedgerRow key={portfolio.id}>
                  <LedgerCell>
                    <Link
                      to="/carteiras/$portfolioId"
                      params={{ portfolioId: portfolio.id }}
                      className="link"
                    >
                      {portfolio.name}
                    </Link>
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
                  <LedgerCell>
                    <Sparkline
                      data={(valuation?.positions ?? []).map((position) =>
                        Number(position.market_value ?? 0),
                      )}
                      width={80}
                      height={20}
                    />
                  </LedgerCell>
                </LedgerRow>
              )
            })}
          </LedgerBody>
        </Ledger>
      </AsyncState>
    </div>
  )
}

function MarketPanel() {
  const { t, locale } = useI18n()
  const overview = useMarketOverview()
  const gainers = overview.data?.gainers ?? []
  const losers = overview.data?.losers ?? []
  const isLive = (overview.data?.quotes ?? []).some((quote) => quote.source !== "seed")

  return (
    <div className="panel">
      <div className="panel-head">
        <h3 className="text-base font-extrabold">{t("dashboard.market")}</h3>
        <span className={isLive ? "live mono text-gold" : "chip muted"}>
          {isLive ? (
            <>
              <i /> {t("markets.live")}
            </>
          ) : (
            t("markets.demo")
          )}
        </span>
      </div>
      <AsyncState isLoading={overview.isLoading} error={overview.error} skeletonRows={8}>
        <Ledger>
          <LedgerHead>
            <LedgerRow>
              <LedgerHeadCell>{t("common.symbol")}</LedgerHeadCell>
              <LedgerHeadCell numeric>{t("common.price")}</LedgerHeadCell>
              <LedgerHeadCell numeric>{t("markets.change")}</LedgerHeadCell>
            </LedgerRow>
          </LedgerHead>
          <LedgerBody>
            {[...gainers, ...losers].slice(0, 10).map((quote) => {
              const change = quote.change_percent ?? 0
              const icon = change >= 0 ? <TrendUp size={13} /> : <TrendDown size={13} />
              return (
                <LedgerRow key={quote.symbol}>
                  <LedgerCell>
                    <Link to="/mercado/$symbol" params={{ symbol: quote.symbol }} className="link">
                      <span className="flex items-center gap-2">
                        {icon}
                        {quote.symbol}
                      </span>
                    </Link>
                  </LedgerCell>
                  <LedgerCell numeric>
                    {formatCurrency(quote.price, quote.currency, locale)}
                  </LedgerCell>
                  <LedgerCell numeric className={toneOf(change) ?? ""}>
                    {percentPointsOrDash(change, locale)}
                  </LedgerCell>
                </LedgerRow>
              )
            })}
          </LedgerBody>
        </Ledger>
      </AsyncState>
    </div>
  )
}

export function DashboardPage() {
  const { t, locale } = useI18n()
  const book = useBookOverview()
  const overview = useMarketOverview()
  const macro = overview.data?.macro ?? []

  return (
    <main className="shell page">
      <PageHeader
        kicker={t("dashboard.kicker")}
        title={t("dashboard.title")}
        subtitle={t("app.description")}
      />

      <MarketTicker />

      <section className="metric-grid" aria-label={t("dashboard.kicker")}>
        <Metric
          label={t("dashboard.aum")}
          value={currencyOrDash(book.data?.total_market_value, "BRL", locale)}
        />
        <Metric
          label={t("dashboard.portfolios")}
          value={formatCompact(book.data?.portfolio_count ?? 0, locale)}
        />
        {macro.slice(0, 4).map((point) => (
          <Metric
            key={point.code}
            label={`${MACRO_LABELS[point.code] ?? point.code} · ${point.unit}`}
            value={Number(point.value).toLocaleString(locale, { maximumFractionDigits: 2 })}
          />
        ))}
      </section>

      <section className="panel-grid two">
        <div className="flex flex-col gap-6 self-stretch">
          <AllocationPanel />
          <TopPortfoliosPanel className="flex-1" />
        </div>
        <MarketPanel />
      </section>
    </main>
  )
}
