import type { ReactNode } from "react"

import { cn } from "../../lib/utils"

export interface FieldProps {
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
  const message = error ?? hint
  const isError = error !== undefined && error !== null
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
      {message ? (
        <p
          role={isError ? "alert" : undefined}
          className={isError ? "text-xs text-destructive" : "text-xs text-ash"}
        >
          {message}
        </p>
      ) : null}
    </div>
  )
}
