import { describe, expect, it } from "vitest"

import { en, pt } from "./messages"

describe("i18n dictionaries", () => {
  it("have exactly the same keys", () => {
    const keys = (dictionary: Record<string, string>) =>
      Object.keys(dictionary).sort((a, b) => a.localeCompare(b))
    expect(keys(en)).toEqual(keys(pt))
  })

  it("have no empty strings", () => {
    const empty = (dictionary: Record<string, string>) =>
      Object.entries(dictionary)
        .filter(([, value]) => value === "")
        .map(([key]) => key)
    expect(empty(pt)).toEqual([])
    expect(empty(en)).toEqual([])
  })

  it("keep interpolation placeholders in sync", () => {
    const placeholders = (value: string) => (value.match(/\{(\w+)\}/g) ?? []).sort()
    const mismatched = (Object.keys(pt) as (keyof typeof pt)[]).filter(
      (key) => placeholders(en[key]).join() !== placeholders(pt[key]).join(),
    )
    expect(mismatched).toEqual([])
  })
})
