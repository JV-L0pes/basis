import * as TooltipPrimitive from "@radix-ui/react-tooltip"
import type { ComponentProps } from "react"

import { cn } from "../../lib/utils"

export const TooltipProvider = TooltipPrimitive.Provider
export const Tooltip = TooltipPrimitive.Root
export const TooltipTrigger = TooltipPrimitive.Trigger

export function TooltipContent({
  className,
  sideOffset = 6,
  ...props
}: ComponentProps<typeof TooltipPrimitive.Content>) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        sideOffset={sideOffset}
        className={cn(
          "z-50 max-w-[16rem] border border-ink bg-paper px-2 py-1 text-xs text-ink",
          className,
        )}
        {...props}
      />
    </TooltipPrimitive.Portal>
  )
}
