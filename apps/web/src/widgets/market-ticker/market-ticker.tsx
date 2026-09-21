import { formatCurrency, formatPercent } from "@basis/ui"

import { useBookOverview, useMarketOverview } from "@/entities/instrument/api"
import { useI18n } from "@/shared/i18n/provider"

/** The ticker band: consolidated AUM plus the main quotes, Ink marquee style. */
export function MarketTicker() {
  const { t, locale } = useI18n()
  const overview = useMarketOverview()
  const book = useBookOverview()

  const quotes = overview.data?.quotes ?? []
  if (quotes.length === 0 && !book.data) return null

  const items = [
    ...(book.data
      ? [
          {
            symbol: t("dashboard.aum"),
            value: formatCurrency(book.data.total_market_value, book.data.currency, locale),
            change: null as number | null,
          },
        ]
      : []),
    ...quotes.slice(0, 12).map((quote) => ({
      symbol: quote.symbol,
      value: formatCurrency(quote.price, quote.currency, locale),
      change: quote.change_percent ?? null,
    })),
  ]

  return (
    <aside className="ticker" aria-label={t("dashboard.market")}>
      <div className="ticker-track">
        {[...items, ...items].map((item) => (
          <span
            key={`${item.symbol}-${item.value}-${String(item.change)}`}
            className="mono flex items-baseline gap-3"
          >
            <span>{item.symbol}</span>
            <span className="tnum">{item.value}</span>
            {item.change !== null ? (
              <span className={item.change >= 0 ? "text-positive" : "text-negative"}>
                {formatPercent(item.change / 100, locale)}
              </span>
            ) : null}
          </span>
        ))}
      </div>
    </aside>
  )
}
