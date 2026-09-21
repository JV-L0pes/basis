import { Skeleton } from "@basis/ui"
import type { ReactNode } from "react"

import { ApiError, toProblem } from "@/shared/api/problem"

export function PageHeader({
  kicker,
  title,
  subtitle,
  actions,
}: {
  kicker: string
  title: string
  subtitle?: string
  actions?: ReactNode
}) {
  return (
    <header className="sec-head">
      <span className="kicker">{kicker}</span>
      <div className="row">
        <div className="max-w-[46ch]">
          <h2 className="text-[clamp(1.75rem,3.5vw,2.75rem)]">{title}</h2>
          {subtitle ? <p className="lede mt-3">{subtitle}</p> : null}
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-3">{actions}</div> : null}
      </div>
    </header>
  )
}

const SKELETON_KEYS = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"] as const

export function AsyncState({
  isLoading,
  error,
  isEmpty,
  emptyLabel,
  children,
  skeletonRows = 4,
}: {
  isLoading: boolean
  error: unknown
  isEmpty?: boolean
  emptyLabel?: string
  children: ReactNode
  skeletonRows?: number
}) {
  if (isLoading) {
    return (
      <div className="flex flex-col gap-2" aria-busy="true">
        {SKELETON_KEYS.slice(0, skeletonRows).map((key) => (
          <Skeleton key={key} />
        ))}
      </div>
    )
  }

  if (error) {
    const problem = toProblem(error)
    return (
      <div className="border border-negative px-5 py-4">
        <p className="mono text-negative">{problem.code}</p>
        <p className="mt-1 text-sm">{problem.detail}</p>
        {error instanceof ApiError && error.problem.errors ? (
          <ul className="mt-2 list-disc pl-5 text-xs text-ash">
            {problem.errors?.map((issue) => (
              <li key={`${issue.loc?.join(".")}-${issue.type}`}>
                {issue.loc?.join(".")}: {issue.msg}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    )
  }

  if (isEmpty) {
    return (
      <div className="border border-rule px-5 py-10 text-center">
        <p className="mono text-ash">{emptyLabel ?? "—"}</p>
      </div>
    )
  }

  return <>{children}</>
}

export function Metric({
  label,
  value,
  delta,
  tone,
}: {
  label: string
  value: string
  delta?: string | null
  tone?: "pos" | "neg" | null
}) {
  return (
    <div className="metric">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{value}</span>
      {delta ? <span className={`metric-delta ${tone ?? ""}`}>{delta}</span> : null}
    </div>
  )
}
