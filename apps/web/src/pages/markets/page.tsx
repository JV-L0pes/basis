import {
  Badge,
  Ledger,
  LedgerBody,
  LedgerCell,
  LedgerHead,
  LedgerHeadCell,
  LedgerRow,
  Skeleton,
} from "@basis/ui"
import { useMemo, useState } from "react"

import { useInstruments, useMarketOverview } from "@/entities/instrument/api"
import { useI18n } from "@/shared/i18n/provider"
import { percentPointsOrDash, toneOf } from "@/shared/lib/display"
import { AsyncState, PageHeader } from "@/shared/ui/primitives"

const CLASSES = ["equity", "fixed_income", "fund", "etf", "real_estate", "crypto"] as const

export function MarketsPage() {
  const { t, locale } = useI18n()
  const [query, setQuery] = useState("")
  const [assetClass, setAssetClass] = useState<string>("")

  const instruments = useInstruments({ query, assetClass: assetClass || undefined })
  const overview = useMarketOverview()

  const changeBySymbol = useMemo(() => {
    const map = new Map<string, number>()
    for (const quote of overview.data?.quotes ?? []) {
      if (quote.change_percent != null) map.set(quote.symbol, quote.change_percent)
    }
    return map
  }, [overview.data])

  const items = instruments.data?.items ?? []

  return (
    <main className="shell page">
      <PageHeader
        kicker={t("markets.kicker")}
        title={t("markets.title")}
        subtitle={t("markets.subtitle")}
      />

      <div className="flex flex-wrap items-end gap-3">
        <input
          className="h-10 min-w-[16rem] flex-1 border border-rule bg-transparent px-3 text-sm focus-visible:border-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={t("markets.searchPlaceholder")}
          aria-label={t("common.search")}
        />
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            className={assetClass === "" ? "chip gold" : "chip muted"}
            onClick={() => setAssetClass("")}
          >
            {t("common.total")}
          </button>
          {CLASSES.map((item) => (
            <button
              key={item}
              type="button"
              className={assetClass === item ? "chip gold" : "chip muted"}
              onClick={() => setAssetClass(item)}
            >
              {t(`assetClass.${item}` as "assetClass.equity")}
            </button>
          ))}
        </div>
      </div>

      <AsyncState
        isLoading={instruments.isLoading}
        error={instruments.error}
        isEmpty={items.length === 0}
        emptyLabel={t("markets.empty")}
      >
        <Ledger>
          <LedgerHead>
            <LedgerRow>
              <LedgerHeadCell>{t("common.symbol")}</LedgerHeadCell>
              <LedgerHeadCell>{t("markets.instruments")}</LedgerHeadCell>
              <LedgerHeadCell>{t("markets.filterClass")}</LedgerHeadCell>
              <LedgerHeadCell>{t("common.status")}</LedgerHeadCell>
              <LedgerHeadCell numeric>{t("markets.change")}</LedgerHeadCell>
            </LedgerRow>
          </LedgerHead>
          <LedgerBody>
            {items.map((instrument) => {
              const change = changeBySymbol.get(instrument.symbol)
              const reference = instrument.isin ? ` · ${instrument.isin}` : ""
              return (
                <LedgerRow key={instrument.id}>
                  <LedgerCell>
                    <a className="link font-semibold" href={`/mercado/${instrument.symbol}`}>
                      {instrument.symbol}
                    </a>
                  </LedgerCell>
                  <LedgerCell>{instrument.name}</LedgerCell>
                  <LedgerCell>
                    <Badge variant="muted">
                      {t(`assetClass.${instrument.asset_class}` as "assetClass.equity")}
                    </Badge>
                  </LedgerCell>
                  <LedgerCell>
                    <span className="mono text-ash">
                      {instrument.currency}
                      {reference}
                    </span>
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

      <section>
        <div className="sec-head">
          <span className="kicker">{t("markets.macro")}</span>
        </div>
        {overview.isLoading ? (
          <Skeleton className="h-20" />
        ) : (
          <div className="metric-grid">
            {(overview.data?.macro ?? []).map((point) => (
              <div className="metric" key={point.code}>
                <span className="metric-label">
                  {point.label} · {point.unit}
                </span>
                <span className="metric-value">
                  {Number(point.value).toLocaleString(locale, { maximumFractionDigits: 2 })}
                </span>
                <span className="metric-delta">{point.date}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </main>
  )
}
