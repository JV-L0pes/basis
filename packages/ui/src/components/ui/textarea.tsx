import type { TextareaHTMLAttributes } from "react"

import { cn } from "../../lib/utils"

export type TextareaProps = TextareaHTMLAttributes<HTMLTextAreaElement>

export function Textarea({ className, rows = 3, ...props }: TextareaProps) {
  return (
    <textarea
      rows={rows}
      className={cn(
        "w-full resize-y border border-rule bg-transparent px-3 py-2 text-sm text-ink placeholder:text-ash",
        "transition-colors duration-300 ease-[var(--ease)] hover:border-ash",
        "focus-visible:border-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  )
}
