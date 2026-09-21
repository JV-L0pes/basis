import type { ReactNode } from "react"

import { cn } from "../../lib/utils"

export type FieldProps = {
  label?: ReactNode
  htmlFor?: string
  hint?: ReactNode
  error?: ReactNode
  required?: boolean
  className?: string
  children: ReactNode
}

/** Label + control + hint/error. The error replaces the hint, per Ink. */
export function Field({ label, htmlFor, hint, error, required, className, children }: FieldProps) {
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {label ? (
        <label
          htmlFor={htmlFor}
          className="font-mono text-[0.58rem] uppercase tracking-[0.14em] text-ash"
        >
          {label}
          {required ? <span aria-hidden="true"> *</span> : null}
        </label>
      ) : null}
      {children}
      {error ? (
        <p role="alert" className="text-xs text-destructive">
          {error}
        </p>
      ) : hint ? (
        <p className="text-xs text-ash">{hint}</p>
      ) : null}
    </div>
  )
}
