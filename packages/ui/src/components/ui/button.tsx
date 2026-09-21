import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"
import type { ButtonHTMLAttributes } from "react"

import { cn } from "../../lib/utils"

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap border font-semibold transition-[background-color,color,border-color] duration-300 ease-[var(--ease)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ink disabled:pointer-events-none disabled:opacity-40 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "border-ink bg-ink text-paper hover:bg-transparent hover:text-ink",
        outline: "border-ink bg-transparent text-ink hover:bg-ink hover:text-paper",
        ghost: "border-transparent bg-transparent text-ink hover:bg-[var(--hover-bg)]",
        danger:
          "border-destructive bg-destructive text-destructive-foreground hover:border-destructive hover:bg-transparent hover:text-destructive",
        link: "border-transparent bg-transparent text-ink underline underline-offset-4 hover:text-ash",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-10 px-4 text-sm",
        lg: "h-12 px-6 text-base",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
)

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    /** Renders the child element instead of a `button` (Radix `asChild`). */
    asChild?: boolean
    /** Swaps the label for a mono loading marker and disables interaction. */
    loading?: boolean
  }

export function Button({
  className,
  variant,
  size,
  asChild = false,
  loading = false,
  disabled,
  children,
  ...props
}: ButtonProps) {
  const Component = asChild ? Slot : "button"
  return (
    <Component
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled ?? loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading ? (
        <span className="mono" aria-hidden="true">
          ···
        </span>
      ) : (
        children
      )}
    </Component>
  )
}
