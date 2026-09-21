import { screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it } from "vitest"

import { ClientsPage } from "@/pages/clients/page"
import { expectNoA11yViolations, renderWithProviders } from "@/test/render"

beforeEach(() => {
  localStorage.setItem("basis-lang", "pt")
})

describe("ClientsPage", () => {
  it("renders the client list returned by the API", async () => {
    renderWithProviders(<ClientsPage />)

    expect(await screen.findByText("Ana Souza")).toBeInTheDocument()
    expect(screen.getByText("ana.souza@basis.dev")).toBeInTheDocument()
    expect(screen.getByText("***.***.247-25")).toBeInTheDocument()
    expect(screen.getByText("Arrojado")).toBeInTheDocument()
    expect(screen.getByText("Ativo")).toBeInTheDocument()
  })

  it("filters through the API when the user searches", async () => {
    renderWithProviders(<ClientsPage />)
    await screen.findByText("Ana Souza")

    await userEvent.type(screen.getByLabelText("Buscar"), "bruno")

    await waitFor(() => {
      expect(screen.getByText("Nenhum cliente cadastrado ainda.")).toBeInTheDocument()
    })
  })

  it("opens the registration dialog from the header action", async () => {
    renderWithProviders(<ClientsPage />)
    await screen.findByText("Ana Souza")

    await userEvent.click(screen.getByRole("button", { name: "Novo cliente" }))

    const dialog = await screen.findByRole("dialog")
    expect(within(dialog).getByLabelText(/nome/i)).toBeInTheDocument()
    expect(within(dialog).getByLabelText(/cpf/i)).toBeInTheDocument()
    expect(within(dialog).getByLabelText(/e-mail/i)).toBeInTheDocument()
  })

  it("has no detectable accessibility violations", async () => {
    const { container } = renderWithProviders(<ClientsPage />)
    await screen.findByText("Ana Souza")

    await expectNoA11yViolations(container)
  })
})
