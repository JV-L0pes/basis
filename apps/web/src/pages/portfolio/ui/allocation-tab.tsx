import type { components } from "@basis/contracts"
import {
  Donut,
  formatBasisPoints,
  formatCurrency,
  formatPercent,
  Ledger,
  LedgerBody,
  LedgerCell,
  LedgerHead,
  LedgerHeadCell,
  LedgerRow,
} from "@basis/ui"
import { useI18n } from "@/shared/i18n/provider"
import { toneOf } from "@/shared/lib/display"

type Analysis = components["schemas"]["AllocationAnalysisResponse"]

export function AllocationTab({ analysis }: { analysis: Analysis | undefined }) {
  const { t, locale } = useI18n()

  if (!analysis) return null

  return (
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
        {analysis.has_targets ? (
          <div className="panel-body">
            <Ledger>
              <LedgerHead>
                <LedgerRow>
                  <LedgerHeadCell>{t("markets.filterClass")}</LedgerHeadCell>
                  <LedgerHeadCell numeric>{t("portfolios.allocation")}</LedgerHeadCell>
                  <LedgerHeadCell numeric>{t("portfolios.targets")}</LedgerHeadCell>
                  <LedgerHeadCell numeric>{t("portfolios.drift")}</LedgerHeadCell>
                  <LedgerHeadCell numeric>{t("portfolios.plan")}</LedgerHeadCell>
                </LedgerRow>
              </LedgerHead>
              <LedgerBody>
                {analysis.drift.map((item) => (
                  <LedgerRow key={item.asset_class}>
                    <LedgerCell>
                      {t(`assetClass.${item.asset_class}` as "assetClass.equity")}
                    </LedgerCell>
                    <LedgerCell numeric>{formatPercent(item.current_weight, locale, 1)}</LedgerCell>
                    <LedgerCell numeric>{formatPercent(item.target_weight, locale, 1)}</LedgerCell>
                    <LedgerCell numeric className={toneOf(item.drift_bps) ?? ""}>
                      {formatBasisPoints(item.drift_bps, locale)}
                    </LedgerCell>
                    <LedgerCell numeric>
                      {formatCurrency(item.delta_value, analysis.currency, locale)}
                    </LedgerCell>
                  </LedgerRow>
                ))}
              </LedgerBody>
            </Ledger>
          </div>
        ) : (
          <div className="panel-body mono text-ash">{t("portfolios.noTargets")}</div>
        )}
      </div>
    </div>
  )
}
