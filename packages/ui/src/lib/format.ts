/**
 * Locale-aware formatters with a module-level cache, so tables with hundreds of
 * rows do not rebuild `Intl.NumberFormat` instances on every render.
 */

type Numeric = number | string | null | undefined

const numberFormats = new Map<string, Intl.NumberFormat>()
const dateFormats = new Map<string, Intl.DateTimeFormat>()

function numeric(value: Numeric): number | null {
  if (value === null || value === undefined || value === "") return null
  const parsed = typeof value === "number" ? value : Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function numberFormat(locale: string, options: Intl.NumberFormatOptions): Intl.NumberFormat {
  const key = `${locale}:${JSON.stringify(options)}`
  const cached = numberFormats.get(key)
  if (cached) return cached
  const created = new Intl.NumberFormat(locale, options)
  numberFormats.set(key, created)
  return created
}

function dateFormat(locale: string, options: Intl.DateTimeFormatOptions): Intl.DateTimeFormat {
  const key = `${locale}:${JSON.stringify(options)}`
  const cached = dateFormats.get(key)
  if (cached) return cached
  const created = new Intl.DateTimeFormat(locale, options)
  dateFormats.set(key, created)
  return created
}

export function formatCurrency(value: Numeric, currency = "BRL", locale = "pt-BR"): string {
  const parsed = numeric(value)
  if (parsed === null) return "—"
  return numberFormat(locale, {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(parsed)
}

export function formatCompact(value: Numeric, locale = "pt-BR"): string {
  const parsed = numeric(value)
  if (parsed === null) return "—"
  return numberFormat(locale, {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(parsed)
}

export function formatQuantity(value: Numeric, locale = "pt-BR"): string {
  const parsed = numeric(value)
  if (parsed === null) return "—"
  return numberFormat(locale, { maximumFractionDigits: 8 }).format(parsed)
}

/** `value` is a fraction: 0.1234 -> "12,34%" */
export function formatPercent(value: Numeric, locale = "pt-BR", digits = 2): string {
  const parsed = numeric(value)
  if (parsed === null) return "—"
  return numberFormat(locale, {
    style: "percent",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(parsed)
}

/** Basis points to a signed percentage string: -125 -> "-1,25%" */
export function formatBasisPoints(value: Numeric, locale = "pt-BR"): string {
  const parsed = numeric(value)
  if (parsed === null) return "—"
  return formatPercent(parsed / 10_000, locale)
}

const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/

/**
 * Parse API values into a Date. Date-only strings (``2026-06-01``) are treated
 * as local dates, otherwise `new Date()` would shift them by the timezone.
 */
function toDate(value: Date | string): Date | null {
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value
  const match = DATE_ONLY.exec(value)
  if (match) {
    const [, year, month, day] = match
    return new Date(Number(year), Number(month) - 1, Number(day))
  }
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export function formatDate(value: Date | string | null | undefined, locale = "pt-BR"): string {
  if (!value) return "—"
  const date = toDate(value)
  if (!date) return "—"
  return dateFormat(locale, { day: "2-digit", month: "2-digit", year: "numeric" }).format(date)
}

export function formatShortDate(value: Date | string | null | undefined, locale = "pt-BR"): string {
  if (!value) return "—"
  const date = toDate(value)
  if (!date) return "—"
  return dateFormat(locale, { day: "2-digit", month: "short" }).format(date)
}

export function formatDateTime(value: Date | string | null | undefined, locale = "pt-BR"): string {
  if (!value) return "—"
  const date = toDate(value)
  if (!date) return "—"
  return dateFormat(locale, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date)
}

export function formatSigned(value: Numeric, formatter: (v: Numeric) => string): string {
  const parsed = numeric(value)
  if (parsed === null) return "—"
  const formatted = formatter(parsed)
  return parsed > 0 ? `+${formatted}` : formatted
}
