import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { I18nProvider } from "@/shared/i18n/provider"
import { LoginForm } from "./login-form"

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => vi.fn().mockResolvedValue(undefined),
}))

vi.mock("@/entities/session/api", () => ({
  login: vi.fn().mockRejectedValue({
    type: "about:blank",
    title: "Authentication required",
    status: 401,
    detail: "Invalid credentials",
    code: "unauthenticated",
  }),
}))

beforeEach(() => {
  // jsdom reports an en-US locale; the copy assertions below are in Portuguese.
  localStorage.setItem("basis-lang", "pt")
})

function renderForm() {
  return render(
    <I18nProvider>
      <LoginForm />
    </I18nProvider>,
  )
}

describe("LoginForm", () => {
  it("renders the required fields", () => {
    renderForm()
    expect(screen.getByLabelText(/e-mail/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/senha/i)).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /entrar/i })).toBeInTheDocument()
  })

  it("blocks submission when the e-mail is invalid", async () => {
    renderForm()
    await userEvent.type(screen.getByLabelText(/e-mail/i), "not-an-email")
    await userEvent.type(screen.getByLabelText(/senha/i), "s3nh4-forte")
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }))

    await waitFor(() => {
      expect(screen.getAllByRole("alert").length).toBeGreaterThan(0)
    })
  })

  it("shows an error alert when the credentials are rejected", async () => {
    renderForm()
    await userEvent.type(screen.getByLabelText(/e-mail/i), "ana@basis.dev")
    await userEvent.type(screen.getByLabelText(/senha/i), "s3nh4-forte")
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }))

    expect(await screen.findByText(/não foi possível entrar/i)).toBeInTheDocument()
  })
})
