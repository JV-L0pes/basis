import * as LabelPrimitive from "@radix-ui/react-label"
import type { ComponentProps } from "react"

import { cn } from "../../lib/utils"

export function Label({ className, ...props }: ComponentProps<typeof LabelPrimitive.Root>) {
  return (
    <LabelPrimitive.Root
      className={cn(
        "font-mono text-[0.58rem] uppercase tracking-[0.14em] text-ash",
        "peer-disabled:cursor-not-allowed peer-disabled:opacity-60",
        className,
      )}
      {...props}
    />
  )
}
