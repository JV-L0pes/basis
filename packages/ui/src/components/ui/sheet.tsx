import * as DialogPrimitive from "@radix-ui/react-dialog"
import type { ComponentProps } from "react"

import { cn } from "../../lib/utils"

export const Sheet = DialogPrimitive.Root
export const SheetTrigger = DialogPrimitive.Trigger
export const SheetClose = DialogPrimitive.Close
export const SheetTitle = DialogPrimitive.Title
export const SheetDescription = DialogPrimitive.Description

export function SheetContent({
  className,
  side = "left",
  children,
  ...props
}: ComponentProps<typeof DialogPrimitive.Content> & { side?: "left" | "right" }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/40" />
      <DialogPrimitive.Content
        className={cn(
          "fixed top-0 z-50 flex h-full w-[min(86vw,22rem)] flex-col border-ink bg-paper p-6 text-ink",
          side === "left" ? "left-0 border-r" : "right-0 border-l",
          className,
        )}
        {...props}
      >
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}
