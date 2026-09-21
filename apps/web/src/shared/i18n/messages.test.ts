import { describe, expect, it } from "vitest"

import { en, pt } from "./messages"

describe("i18n dictionaries", () => {
  it("have exactly the same keys", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(pt).sort())
  })

  it("have no empty strings", () => {
    for (const [key, value] of Object.entries(pt)) {
      expect(value, `pt.${key}`).not.toBe("")
    }
    for (const [key, value] of Object.entries(en)) {
      expect(value, `en.${key}`).not.toBe("")
    }
  })

  it("keep interpolation placeholders in sync", () => {
    const placeholders = (value: string) => (value.match(/\{(\w+)\}/g) ?? []).sort()
    for (const key of Object.keys(pt) as (keyof typeof pt)[]) {
      expect(placeholders(en[key]), key).toEqual(placeholders(pt[key]))
    }
  })
})
