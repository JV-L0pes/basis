import type { components } from "@basis/contracts"
import {
  Badge,
  formatCurrency,
  formatDate,
  Ledger,
  LedgerBody,
  LedgerCell,
  LedgerHead,
  LedgerHeadCell,
  LedgerRow,
} from "@basis/ui"

import { useI18n } from "@/shared/i18n/provider"

type Transaction = components["schemas"]["TransactionResponse"]

function kindVariant(kind: string): "neutral" | "gold" | "muted" {
  if (kind === "buy") return "neutral"
  if (kind === "sell") return "gold"
  return "muted"
}

export function LedgerTab({
  transactions,
  baseCurrency,
}: {
  transactions: Transaction[]
  baseCurrency: string
}) {
  const { t, locale } = useI18n()

  return (
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
        {transactions.map((transaction) => (
          <LedgerRow key={transaction.id}>
            <LedgerCell>{formatDate(transaction.trade_date, locale)}</LedgerCell>
            <LedgerCell>
              <Badge variant={kindVariant(transaction.kind)}>
                {t(`transactionKind.${transaction.kind}` as "transactionKind.buy")}
              </Badge>
            </LedgerCell>
            <LedgerCell>{transaction.symbol}</LedgerCell>
            <LedgerCell numeric>{transaction.quantity}</LedgerCell>
            <LedgerCell numeric>
              {formatCurrency(transaction.price, baseCurrency, locale)}
            </LedgerCell>
            <LedgerCell numeric>
              {formatCurrency(transaction.gross_value, baseCurrency, locale)}
            </LedgerCell>
          </LedgerRow>
        ))}
      </LedgerBody>
    </Ledger>
  )
}
