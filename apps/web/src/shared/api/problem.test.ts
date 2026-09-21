import { describe, expect, it } from "vitest"

import { ApiError, fieldErrors, isProblem, toProblem } from "./problem"

describe("problem details", () => {
  it("recognises a problem payload", () => {
    const problem = {
      type: "https://basis.dev/problems/not_found",
      title: "Resource not found",
      status: 404,
      detail: "Client not found",
      code: "not_found",
    }
    expect(isProblem(problem)).toBe(true)
  })

  it("rejects arbitrary objects", () => {
    expect(isProblem({ message: "nope" })).toBe(false)
    expect(isProblem(null)).toBe(false)
    expect(isProblem("boom")).toBe(false)
  })

  it("normalises unknown errors", () => {
    const problem = toProblem(new Error("boom"))
    expect(problem.code).toBe("unknown_error")
    expect(problem.detail).toBe("boom")
  })

  it("preserves ApiError details", () => {
    const error = new ApiError({
      type: "about:blank",
      title: "Conflict",
      status: 409,
      detail: "Tax id already registered",
      code: "conflict",
    })
    expect(toProblem(error).code).toBe("conflict")
    expect(error.status).toBe(409)
  })

  it("extracts field errors from validation issues", () => {
    const fields = fieldErrors({
      type: "about:blank",
      title: "Validation error",
      status: 422,
      detail: "invalid payload",
      code: "validation_error",
      errors: [
        { loc: ["body", "email"], msg: "Invalid e-mail address", type: "value_error" },
        { loc: ["body", "tax_id"], msg: "Tax id check digits are invalid" },
      ],
    })
    expect(fields).toEqual({
      email: "Invalid e-mail address",
      tax_id: "Tax id check digits are invalid",
    })
  })
})
