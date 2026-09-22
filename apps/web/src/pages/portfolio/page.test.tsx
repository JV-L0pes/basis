import { screen, within } from "@testing-library/react"
import { beforeEach, describe, expect, it } from "vitest"

import { PortfolioPage } from "@/pages/portfolio/page"
import { expectNoA11yViolations, renderWithProviders } from "@/test/render"
import { setTestRoute } from "@/test/router-stub"

beforeEach(() => {
  localStorage.setItem("basis-lang", "pt")
  setTestRoute({ params: { portfolioId: "01920000-0000-7000-8000-000000000201" } })
})

describe("PortfolioPage", () => {
  it("renders the valuation metrics of the portfolio", async () => {
    const { container } = renderWithProviders(<PortfolioPage />)

    expect(await screen.findByRole("heading", { name: "Carteira Ana" })).toBeInTheDocument()
    const metrics = container.querySelector<HTMLElement>(".metric-grid")!
    expect(within(metrics).getByText("Valor de mercado")).toBeInTheDocument()
    expect(within(metrics).getByText(/12\.000,00/)).toBeInTheDocument()
    expect(within(metrics).getByText(/10\.000,00/)).toBeInTheDocument()
    expect(within(metrics).getByText(/21,30%/)).toBeInTheDocument()
  })

  it("lists positions with market value and P&L", async () => {
    renderWithProviders(<PortfolioPage />)
    await screen.findByRole("heading", { name: "Carteira Ana" })

    expect(screen.getByRole("link", { name: "PETR4" })).toBeInTheDocument()
    expect(screen.getAllByText(/7\.744,00/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/714,00/).length).toBeGreaterThan(0)
  })

  it("has no detectable accessibility violations", async () => {
    const { container } = renderWithProviders(<PortfolioPage />)
    await screen.findByRole("heading", { name: "Carteira Ana" })

    await expectNoA11yViolations(container)
  })
})
