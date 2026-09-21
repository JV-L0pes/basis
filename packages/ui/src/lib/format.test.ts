import { describe, expect, it } from "vitest"

import {
  formatBasisPoints,
  formatCompact,
  formatCurrency,
  formatDate,
  formatDateTime,
  formatPercent,
  formatQuantity,
  formatSigned,
} from "./format"

const NBSP = "\u00a0"

describe("formatCurrency", () => {
  it("formats BRL in pt-BR", () => {
    expect(formatCurrency(1234.5, "BRL", "pt-BR")).toBe(`R$${NBSP}1.234,50`)
  })

  it("formats USD in en-US", () => {
    expect(formatCurrency("1234.5", "USD", "en-US")).toBe("$1,234.50")
  })

  it("handles negatives, zero and missing values", () => {
    expect(formatCurrency(-10, "BRL", "pt-BR")).toBe(`-R$${NBSP}10,00`)
    expect(formatCurrency(0, "BRL", "pt-BR")).toBe(`R$${NBSP}0,00`)
    expect(formatCurrency(null, "BRL", "pt-BR")).toBe("—")
    expect(formatCurrency(undefined, "BRL", "pt-BR")).toBe("—")
    expect(formatCurrency("not-a-number", "BRL", "pt-BR")).toBe("—")
  })
})

describe("formatPercent", () => {
  it("treats the value as a fraction", () => {
    expect(formatPercent(0.1234)).toBe("12,34%")
    expect(formatPercent(-0.05)).toBe("-5,00%")
  })

  it("supports custom digits", () => {
    expect(formatPercent(0.12345, "pt-BR", 4)).toBe("12,3450%")
  })
})

describe("formatBasisPoints", () => {
  it("converts basis points to percent", () => {
    expect(formatBasisPoints(-125)).toBe("-1,25%")
    expect(formatBasisPoints(1000)).toBe("10,00%")
  })
})

describe("formatQuantity", () => {
  it("keeps fractional quantities readable", () => {
    expect(formatQuantity("0.015")).toBe("0,015")
    expect(formatQuantity(200)).toBe("200")
  })
})

describe("formatCompact", () => {
  it("compacts large numbers", () => {
    expect(formatCompact(1_250_000, "pt-BR")).toMatch(/1,3\s?mi/i)
  })
})

describe("formatDate", () => {
  it("formats date-only ISO strings without shifting the day", () => {
    expect(formatDate("2026-06-01")).toBe("01/06/2026")
  })

  it("formats full timestamps", () => {
    expect(formatDateTime("2026-06-01T12:34:56Z")).toMatch(/\d{2}\/\d{2}\/2026/)
  })

  it("returns the placeholder for invalid input", () => {
    expect(formatDate("nope")).toBe("—")
    expect(formatDate(null)).toBe("—")
  })
})

describe("formatSigned", () => {
  it("prefixes positive values", () => {
    expect(formatSigned(10, (value) => formatCurrency(value, "BRL"))).toBe(`+R$${NBSP}10,00`)
    expect(formatSigned(-10, (value) => formatCurrency(value, "BRL"))).toBe(`-R$${NBSP}10,00`)
    expect(formatSigned(0, (value) => formatCurrency(value, "BRL"))).toBe(`R$${NBSP}0,00`)
  })
})
