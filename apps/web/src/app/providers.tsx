import { Toaster } from "@basis/ui"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { type ReactNode, useEffect, useState } from "react"

import { me } from "@/entities/session/api"
import { useSessionStore } from "@/entities/session/store"
import { refreshAccessToken } from "@/shared/api/client"
import { ApiError } from "@/shared/api/problem"
import { I18nProvider } from "@/shared/i18n/provider"
import { sessionBootstrap } from "@/shared/session-bootstrap"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status < 500) return false
        return failureCount < 2
      },
    },
    mutations: { retry: 0 },
  },
})

/**
 * Restores the session on boot: the refresh cookie is exchanged for an access
 * token (memory only), then the profile is fetched. Renders children either
 * way — protected routes redirect to /login when there is no session.
 */
function SessionBootstrap({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false)
  const setSession = useSessionStore((state) => state.setSession)

  useEffect(() => {
    let cancelled = false
    async function restore() {
      const token = await refreshAccessToken()
      if (cancelled) return
      if (token) {
        try {
          const user = await me()
          if (!cancelled) {
            setSession({ user, accessToken: token, expiresIn: 900 })
          }
        } catch {
          /* the token was valid but the profile failed — keep the session empty */
        }
      }
      if (!cancelled) setReady(true)
      sessionBootstrap.complete()
    }
    void restore()
    return () => {
      cancelled = true
    }
  }, [setSession])

  return (
    <>
      {children}
      <span hidden aria-live="polite">
        {ready ? "ready" : "loading"}
      </span>
    </>
  )
}

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <I18nProvider>
        <SessionBootstrap>{children}</SessionBootstrap>
        <Toaster />
      </I18nProvider>
    </QueryClientProvider>
  )
}

export { queryClient }
