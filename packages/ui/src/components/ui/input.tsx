import type { InputHTMLAttributes } from "react"

import { cn } from "../../lib/utils"

export type InputProps = InputHTMLAttributes<HTMLInputElement>

export function Input({ className, type = "text", ...props }: InputProps) {
  return (
    <input
      type={type}
      className={cn(
        "h-10 w-full border border-rule bg-transparent px-3 text-sm text-ink placeholder:text-ash",
        "transition-colors duration-300 ease-[var(--ease)] hover:border-ash",
        "focus-visible:border-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "aria-[invalid=true]:border-destructive",
        className,
      )}
      {...props}
    />
  )
}
