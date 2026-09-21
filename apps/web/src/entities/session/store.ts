import type { components } from "@basis/contracts"
import { create } from "zustand"

export type User = components["schemas"]["UserResponse"]

type SessionState = {
  user: User | null
  accessToken: string | null
  /** Unix milliseconds at which the access token expires. */
  expiresAt: number | null
  setSession: (session: { user: User; accessToken: string; expiresIn: number }) => void
  clear: () => void
  isAuthenticated: () => boolean
}

/**
 * The access token lives only in memory (never localStorage); the refresh token
 * is an httpOnly cookie, so a reload restores the session through `/auth/refresh`.
 */
export const useSessionStore = create<SessionState>((set, get) => ({
  user: null,
  accessToken: null,
  expiresAt: null,
  setSession: ({ user, accessToken, expiresIn }) =>
    set({ user, accessToken, expiresAt: Date.now() + expiresIn * 1000 }),
  clear: () => set({ user: null, accessToken: null, expiresAt: null }),
  isAuthenticated: () => get().user !== null && get().accessToken !== null,
}))
