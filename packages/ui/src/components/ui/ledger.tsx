import type { HTMLAttributes, TdHTMLAttributes } from "react"

import { cn } from "../../lib/utils"

/**
 * Ledger — the financial data table of the Ink system: hairline rows, mono
 * uppercase headers over a 2px ink rule, tabular numbers, no card wrapper.
 */
export function Ledger({ className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return <table className={cn("ledger", className)} {...props} />
}

export function LedgerHead({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={className} {...props} />
}

export function LedgerBody({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={className} {...props} />
}

export function LedgerRow({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={className} {...props} />
}

export type LedgerCellProps = TdHTMLAttributes<HTMLTableCellElement> & {
  numeric?: boolean
}

export function LedgerHeadCell({ className, numeric, ...props }: LedgerCellProps) {
  return <th scope="col" className={cn(numeric && "num", className)} {...props} />
}

export function LedgerCell({ className, numeric, ...props }: LedgerCellProps) {
  return <td className={cn(numeric && "num", className)} {...props} />
}

interface ValueProps {
  value: number | string | null | undefined
  format: (value: number | string | null | undefined) => string
  className?: string
}

function toneOf(value: number | null): "pos" | "neg" | undefined {
  if (value === null || value === 0) return undefined
  return value > 0 ? "pos" : "neg"
}

/** A signed value rendered in the value colours (positive/negative). */
export function LedgerValue({ value, format, className }: ValueProps) {
  const parsed = value === null || value === undefined ? null : Number(value)
  const isFiniteValue = parsed !== null && !Number.isNaN(parsed)
  const tone = isFiniteValue ? toneOf(parsed) : undefined
  const sign = isFiniteValue && parsed > 0 ? "+" : ""
  return (
    <span className={cn(tone, className)}>
      {sign}
      {format(value)}
    </span>
  )
}
