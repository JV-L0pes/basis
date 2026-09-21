import { formatCurrency, formatPercent } from "@basis/ui"

export type Tone = "pos" | "neg" | null

/** Fraction (0.21) to a locale percent string, or an em dash when missing. */
export function percentOrDash(value: number | null | undefined, locale: string): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—"
  return formatPercent(value, locale)
}

/** Raw percentage points (21.3) to a locale percent string. */
export function percentPointsOrDash(value: number | null | undefined, locale: string): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—"
  return formatPercent(value / 100, locale)
}

export function currencyOrDash(
  value: string | number | null | undefined,
  currency: string,
  locale: string,
): string {
  if (value === null || value === undefined || value === "") return "—"
  return formatCurrency(value, currency, locale)
}

export function toneOf(value: string | number | null | undefined): Tone {
  if (value === null || value === undefined) return null
  const parsed = Number(value)
  if (!Number.isFinite(parsed) || parsed === 0) return null
  return parsed > 0 ? "pos" : "neg"
}
