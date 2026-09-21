import * as TabsPrimitive from "@radix-ui/react-tabs"
import type { ComponentProps } from "react"

import { cn } from "../../lib/utils"

export const Tabs = TabsPrimitive.Root

export function TabsList({ className, ...props }: ComponentProps<typeof TabsPrimitive.List>) {
  return (
    <TabsPrimitive.List
      className={cn("flex items-center gap-6 border-b border-rule", className)}
      {...props}
    />
  )
}

export function TabsTrigger({ className, ...props }: ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "border-b-2 border-transparent px-1 pb-2 font-mono text-[0.6rem] uppercase tracking-[0.14em] text-ash",
        "transition-colors duration-300 ease-[var(--ease)] hover:text-ink",
        "data-[state=active]:border-ink data-[state=active]:text-ink",
        className,
      )}
      {...props}
    />
  )
}

export function TabsContent({ className, ...props }: ComponentProps<typeof TabsPrimitive.Content>) {
  return <TabsPrimitive.Content className={cn("pt-5 outline-none", className)} {...props} />
}
