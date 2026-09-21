import type { ComponentProps } from "react"
import { Toaster as Sonner, toast } from "sonner"

/** Ink-styled toasts: squared, hairline border, mono description. */
export function Toaster({ ...props }: ComponentProps<typeof Sonner>) {
  return (
    <Sonner
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast:
            "border border-ink bg-paper text-ink shadow-none rounded-none font-[var(--font-display)]",
          title: "text-sm font-semibold tracking-[-0.01em]",
          description: "text-xs text-ash",
          actionButton: "border border-ink bg-ink text-paper rounded-none",
          cancelButton: "border border-rule text-ash rounded-none",
          error: "border-negative text-ink",
          success: "border-ink text-ink",
        },
      }}
      {...props}
    />
  )
}

export { toast }
