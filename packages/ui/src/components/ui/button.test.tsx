import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { Button } from "./button"

describe("Button", () => {
  it("renders the primary variant by default", () => {
    render(<Button>Alocar</Button>)
    const button = screen.getByRole("button", { name: "Alocar" })
    expect(button).toBeInTheDocument()
    expect(button.className).toContain("bg-ink")
  })

  it("applies size and variant classes", () => {
    render(
      <Button variant="outline" size="sm">
        Editar
      </Button>,
    )
    const button = screen.getByRole("button", { name: "Editar" })
    expect(button.className).toContain("border-ink")
    expect(button.className).toContain("h-8")
  })

  it("fires the click handler", async () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Salvar</Button>)
    await userEvent.click(screen.getByRole("button", { name: "Salvar" }))
    expect(onClick).toHaveBeenCalledOnce()
  })

  it("is disabled and busy while loading", () => {
    render(<Button loading>Salvar</Button>)
    const button = screen.getByRole("button")
    expect(button).toBeDisabled()
    expect(button).toHaveAttribute("aria-busy", "true")
  })

  it("supports asChild composition", () => {
    render(
      <Button asChild>
        <a href="/clientes">Clientes</a>
      </Button>,
    )
    const link = screen.getByRole("link", { name: "Clientes" })
    expect(link).toHaveAttribute("href", "/clientes")
    expect(link.className).toContain("bg-ink")
  })
})
