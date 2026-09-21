import { cva, type VariantProps } from "class-variance-authority"
import type { HTMLAttributes } from "react"

import { cn } from "../../lib/utils"

const badgeVariants = cva(
  "inline-flex items-center gap-1 border px-2 py-[0.15rem] font-mono text-[0.55rem] uppercase tracking-[0.12em] whitespace-nowrap",
  {
    variants: {
      variant: {
        neutral: "border-ink text-ink",
        muted: "border-rule text-ash",
        positive: "border-positive text-positive",
        negative: "border-negative text-negative",
        gold: "border-gold text-gold",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
)

export type BadgeProps = HTMLAttributes<HTMLSpanElement> & VariantProps<typeof badgeVariants>

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}
