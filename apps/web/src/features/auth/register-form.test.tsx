import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { I18nProvider } from "@/shared/i18n/provider"
import { RegisterForm } from "./register-form"

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn().mockResolvedValue(undefined),
}))

vi.mock("@/entities/session/api", () => ({
  register: vi.fn().mockRejectedValue({
    type: "about:blank",
    title: "Conflict",
    status: 409,
    detail: "E-mail is already registered",
    code: "conflict",
  }),
}))

beforeEach(() => {
  // jsdom reports an en-US locale; the copy assertions below are in Portuguese.
  localStorage.setItem("basis-lang", "pt")
})

function renderForm() {
  return render(
    <I18nProvider>
      <RegisterForm />
    </I18nProvider>,
  )
}

describe("RegisterForm", () => {
  it("renders the required fields", () => {
    renderForm()
    expect(screen.getByLabelText(/nome completo/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/e-mail/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/senha/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /criar conta/i })).toBeInTheDocument()
  })

  it("blocks submission when the password is too short", async () => {
    renderForm()
    await userEvent.type(screen.getByLabelText(/nome completo/i), "Ana Souza")
    await userEvent.type(screen.getByLabelText(/e-mail/i), "ana@basis.dev")
    await userEvent.type(screen.getByLabelText(/senha/i), "curta1")
    await userEvent.click(screen.getByRole("button", { name: /criar conta/i }))

    await waitFor(() => {
      expect(screen.getAllByRole("alert").length).toBeGreaterThan(0)
    })
  })

  it("shows an alert when the e-mail is already taken", async () => {
    renderForm()
    await userEvent.type(screen.getByLabelText(/nome completo/i), "Ana Souza")
    await userEvent.type(screen.getByLabelText(/e-mail/i), "ana@basis.dev")
    await userEvent.type(screen.getByLabelText(/senha/i), "s3nh4-forte")
    await userEvent.click(screen.getByRole("button", { name: /criar conta/i }))

    expect(await screen.findByText(/já existe uma conta/i)).toBeInTheDocument()
  })
})
