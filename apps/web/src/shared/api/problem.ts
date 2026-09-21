/** RFC 9457 problem details, as produced by the Basis API. */

export type ValidationIssue = {
  loc?: string[]
  msg?: string
  type?: string
}

export type ProblemDetails = {
  type: string
  title: string
  status: number
  detail: string
  code: string
  instance?: string
  request_id?: string
  errors?: ValidationIssue[]
}

export class ApiError extends Error {
  readonly problem: ProblemDetails

  constructor(problem: ProblemDetails) {
    super(problem.detail || problem.title)
    this.name = "ApiError"
    this.problem = problem
  }

  get status(): number {
    return this.problem.status
  }

  get code(): string {
    return this.problem.code
  }
}

const FALLBACK: ProblemDetails = {
  type: "about:blank",
  title: "Erro inesperado",
  status: 0,
  detail: "Não foi possível concluir a operação.",
  code: "unknown_error",
}

export function isProblem(value: unknown): value is ProblemDetails {
  if (typeof value !== "object" || value === null) return false
  const candidate = value as Record<string, unknown>
  return typeof candidate.code === "string" && typeof candidate.status === "number"
}

/** Normalise anything thrown by the API layer into problem details. */
export function toProblem(error: unknown): ProblemDetails {
  if (error instanceof ApiError) return error.problem
  if (isProblem(error)) return error
  if (error instanceof Error) {
    return { ...FALLBACK, detail: error.message }
  }
  return FALLBACK
}

export function fieldErrors(problem: ProblemDetails): Record<string, string> {
  const fields: Record<string, string> = {}
  for (const issue of problem.errors ?? []) {
    const field = issue.loc?.at(-1)
    if (field && issue.msg && !fields[field]) fields[field] = issue.msg
  }
  return fields
}
