import { render } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { Donut } from "./donut"
import { Sparkline } from "./sparkline"

describe("Sparkline", () => {
  it("renders a polyline for a series", () => {
    const { container } = render(<Sparkline data={[10, 12, 11, 15]} />)
    const polyline = container.querySelector("polyline")
    expect(polyline).not.toBeNull()
    expect(polyline?.getAttribute("points")).not.toContain("NaN")
  })

  it("renders nothing with fewer than two points", () => {
    const { container } = render(<Sparkline data={[10]} />)
    expect(container.querySelector("svg")).toBeNull()
  })

  it("renders nothing for empty data", () => {
    const { container } = render(<Sparkline data={[]} />)
    expect(container.querySelector("svg")).toBeNull()
  })

  it("uses the negative colour when the series falls", () => {
    const { container } = render(<Sparkline data={[15, 12, 9]} />)
    const polyline = container.querySelector("polyline")
    expect(polyline?.getAttribute("stroke")).toBe("var(--negative)")
  })
})

describe("Donut", () => {
  it("renders one arc per slice and the total", () => {
    const { container } = render(
      <Donut
        data={[
          { label: "Renda variável", value: 6000 },
          { label: "Renda fixa", value: 4000 },
        ]}
      />,
    )
    expect(container.querySelectorAll("circle")).toHaveLength(2)
    expect(container.textContent).toContain("10.000,00")
  })

  it("renders an empty state when there is nothing to show", () => {
    const { container } = render(<Donut data={[]} />)
    expect(container.querySelectorAll("circle")).toHaveLength(0)
    expect(container.textContent).toContain("Sem posições")
  })

  it("skips non-positive slices", () => {
    const { container } = render(
      <Donut
        data={[
          { label: "Caixa", value: 1000 },
          { label: "Zerado", value: 0 },
        ]}
      />,
    )
    expect(container.querySelectorAll("circle")).toHaveLength(1)
  })
})
