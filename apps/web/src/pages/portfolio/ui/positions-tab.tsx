import type { components } from "@basis/contracts"
import {
  formatCurrency,
  Ledger,
  LedgerBody,
  LedgerCell,
  LedgerHead,
  LedgerHeadCell,
  LedgerRow,
} from "@basis/ui"
import { Link } from "@tanstack/react-router"

import { useI18n } from "@/shared/i18n/provider"
import { percentOrDash, toneOf } from "@/shared/lib/display"

type Position = components["schemas"]["PositionValuationResponse"]

export function PositionsTab({
  positions,
  unpriced,
  baseCurrency,
}: {
  positions: Position[]
  unpriced: string[]
  baseCurrency: string
}) {
  const { t, locale } = useI18n()

  return (
    <>
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
          {positions.map((position) => (
            <LedgerRow key={position.symbol}>
              <LedgerCell>
                <Link to="/mercado/$symbol" params={{ symbol: position.symbol }} className="link">
                  {position.symbol}
                </Link>
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
              <LedgerCell numeric className={toneOf(position.unrealized_gain) ?? ""}>
                {position.unrealized_gain
                  ? formatCurrency(position.unrealized_gain, position.currency, locale)
                  : "—"}
              </LedgerCell>
              <LedgerCell numeric>
                {position.weight !== null ? percentOrDash(position.weight, locale) : "—"}
              </LedgerCell>
            </LedgerRow>
          ))}
        </LedgerBody>
      </Ledger>
      {unpriced.length > 0 ? (
        <p className="mono mt-3 text-ash">
          {t("portfolios.unpriced")}: {unpriced.join(", ")} ({baseCurrency})
        </p>
      ) : null}
    </>
  )
}
