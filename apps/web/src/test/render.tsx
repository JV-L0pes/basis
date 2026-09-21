import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { type RenderResult, render } from "@testing-library/react"
import axe from "axe-core"
import type { ReactElement, ReactNode } from "react"
import { expect } from "vitest"

import { I18nProvider } from "@/shared/i18n/provider"

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 },
      mutations: { retry: false },
    },
  })
}

function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={createTestQueryClient()}>
      <I18nProvider>{children}</I18nProvider>
    </QueryClientProvider>
  )
}

/** Render a component with the app providers (fresh query client per test). */
export function renderWithProviders(ui: ReactElement): RenderResult {
  return render(ui, { wrapper: Providers })
}

/** Assert that the rendered tree has no axe-core violations. */
export async function expectNoA11yViolations(container: HTMLElement): Promise<void> {
  const results = await axe.run(container, {
    rules: {
      // jsdom has no layout, so contrast cannot be measured here.
      "color-contrast": { enabled: false },
    },
  })
  const summary = results.violations.map((violation) => ({
    id: violation.id,
    impact: violation.impact,
    nodes: violation.nodes.map((node) => node.target.join(" ")),
  }))
  expect(summary).toEqual([])
}
