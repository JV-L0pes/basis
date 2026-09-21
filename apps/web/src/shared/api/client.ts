import type { components, paths } from "@basis/contracts"
import createClient from "openapi-fetch"

import { ApiError, isProblem, type ProblemDetails } from "@/shared/api/problem"
import { env } from "@/shared/config/env"

type AuthResponse = components["schemas"]["AuthResponse"]

const RETRY_HEADER = "x-basis-retry"

/**
 * Auth wiring injected by the application layer (`app/providers`). Keeping it as
 * a bridge lets `shared` stay free of `entities` imports, as FSD requires.
 */
interface AuthBridge {
  getAccessToken: () => string | null
  onSession: (session: AuthResponse) => void
  onSignedOut: () => void
}

const bridge: AuthBridge = {
  getAccessToken: () => null,
  onSession: () => undefined,
  onSignedOut: () => undefined,
}

export function configureAuth(next: Partial<AuthBridge>): void {
  Object.assign(bridge, next)
}

export async function refreshAccessToken(): Promise<string | null> {
  try {
    const response = await fetch(`${env.apiUrl}/api/v1/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    })
    if (!response.ok) return null
    const payload: unknown = await response.json()
    const body = payload as AuthResponse
    bridge.onSession(body)
    return body.token.access_token
  } catch {
    return null
  }
}

/**
 * Fetch wrapper that attaches the in-memory access token and, on a 401,
 * exchanges the refresh cookie for a new token and replays the request once.
 */
async function authAwareFetch(
  input: Request | string | URL,
  init?: RequestInit,
): Promise<Response> {
  const build = (token: string | null, retried: boolean) => {
    const source = input instanceof Request ? input : undefined
    const headers = new Headers(init?.headers ?? source?.headers)
    if (token) headers.set("Authorization", `Bearer ${token}`)
    if (retried) headers.set(RETRY_HEADER, "1")
    return source
      ? new Request(source, { headers, credentials: "include" })
      : new Request(input, { ...init, headers, credentials: "include" })
  }

  let response = await fetch(build(bridge.getAccessToken(), false))
  if (response.status === 401) {
    const token = await refreshAccessToken()
    if (token) {
      response = await fetch(build(token, true))
    } else {
      bridge.onSignedOut()
    }
  }
  return response
}

export const api = createClient<paths>({
  baseUrl: env.apiUrl,
  credentials: "include",
  fetch: authAwareFetch,
})

/** Unwrap an openapi-fetch result, throwing a typed error on failure. */
export async function unwrap<T>(
  result: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await result
  if (error !== undefined) {
    const problem: ProblemDetails = isProblem(error)
      ? error
      : {
          type: "about:blank",
          title: response.statusText || "Request failed",
          status: response.status,
          detail: "A requisição falhou.",
          code: `http_${response.status}`,
        }
    throw new ApiError(problem)
  }
  if (data === undefined) {
    throw new ApiError({
      type: "about:blank",
      title: "Empty response",
      status: response.status,
      detail: "O servidor não retornou dados.",
      code: "empty_response",
    })
  }
  return data
}
