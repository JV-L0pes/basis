import { screen, within } from "@testing-library/react"
import { beforeEach, describe, expect, it } from "vitest"

import { DashboardPage } from "@/pages/dashboard/page"
import { expectNoA11yViolations, renderWithProviders } from "@/test/render"

beforeEach(() => {
  localStorage.setItem("basis-lang", "pt")
})

describe("DashboardPage", () => {
  it("shows the assets under management and portfolio count", async () => {
    const { container } = renderWithProviders(<DashboardPage />)

    // The AUM appears both in the ticker band and in the metric grid.
    expect((await screen.findAllByText(/168\.000,00/)).length).toBeGreaterThan(0)

    const metrics = container.querySelector(".metric-grid")
    expect(metrics).not.toBeNull()
    expect(within(metrics as HTMLElement).getByText("Patrimônio sob gestão")).toBeInTheDocument()
    expect(within(metrics as HTMLElement).getAllByText("Carteiras").length).toBeGreaterThan(0)
  })

  it("shows macro indicators from the market overview", async () => {
    const { container } = renderWithProviders(<DashboardPage />)
    await screen.findAllByText(/168\.000,00/)

    const metrics = container.querySelector<HTMLElement>(".metric-grid")!
    expect(within(metrics).getByText(/SELIC/i)).toBeInTheDocument()
    expect(within(metrics).getByText(/10,75/)).toBeInTheDocument()
  })

  it("lists the largest portfolios with their valuation", async () => {
    renderWithProviders(<DashboardPage />)

    const link = await screen.findByRole("link", { name: "Carteira Ana" })
    const row = link.closest("tr")
    expect(row).not.toBeNull()
    expect(within(row as HTMLElement).getByText(/12\.000,00/)).toBeInTheDocument()
  })

  it("has no detectable accessibility violations", async () => {
    const { container } = renderWithProviders(<DashboardPage />)
    await screen.findAllByText(/168\.000,00/)

    await expectNoA11yViolations(container)
  })
})
