import type { components } from "@basis/contracts"

import { api, unwrap } from "@/shared/api/client"

export type AuthResponse = components["schemas"]["AuthResponse"]
export type User = components["schemas"]["UserResponse"]

export function login(email: string, password: string): Promise<AuthResponse> {
  return unwrap(api.POST("/api/v1/auth/login", { body: { email, password } }))
}

export function register(
  email: string,
  password: string,
  displayName: string,
): Promise<AuthResponse> {
  return unwrap(
    api.POST("/api/v1/auth/register", {
      body: { email, password, display_name: displayName },
    }),
  )
}

export function logout(): Promise<void> {
  return unwrap(api.POST("/api/v1/auth/logout", { body: {} })).then(() => undefined)
}

export function me(): Promise<User> {
  return unwrap(api.GET("/api/v1/auth/me"))
}
