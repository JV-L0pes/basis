import type { ComponentProps } from "react"
import { Toaster as Sonner, toast } from "sonner"

/**
 * Ink-styled toasts. Sonner's own chrome is turned off (`unstyled`) so the
 * component is fully expressed with the design system: hairline border, square
 * corners, compact padding, no shadow.
 */
export function Toaster({ ...props }: ComponentProps<typeof Sonner>) {
  return (
    <Sonner
      position="top-right"
      closeButton
      gap={8}
      offset={16}
      toastOptions={{
        unstyled: true,
        classNames: {
          toast: "flex w-full items-start gap-3 border border-ink bg-paper px-4 py-3 text-ink",
          title: "text-sm font-semibold tracking-[-0.01em]",
          description: "text-xs text-ash",
          icon: "mt-[0.15rem] flex-none",
          actionButton:
            "mono ml-auto border border-ink bg-ink px-2 py-1 text-paper transition-colors hover:bg-transparent hover:text-ink",
          cancelButton:
            "mono ml-2 border border-rule px-2 py-1 text-ash transition-colors hover:border-ink hover:text-ink",
          closeButton:
            "absolute -top-2 -left-2 grid h-5 w-5 place-items-center border border-ink bg-paper text-[0.6rem] text-ink",
          success: "border-ink",
          error: "border-negative",
          warning: "border-gold",
          info: "border-rule",
        },
      }}
      {...props}
    />
  )
}

export { toast }
