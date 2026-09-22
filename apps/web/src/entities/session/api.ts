import type { components } from "@basis/contracts"

import { api, unwrap } from "@/shared/api/client"

export type AuthResponse = components["schemas"]["AuthResponse"]
export type User = components["schemas"]["UserResponse"]

export interface RegisterInput {
  display_name: string
  email: string
  password: string
}

export function login(email: string, password: string): Promise<AuthResponse> {
  return unwrap(api.POST("/api/v1/auth/login", { body: { email, password } }))
}

export function register(input: RegisterInput): Promise<AuthResponse> {
  return unwrap(api.POST("/api/v1/auth/register", { body: input }))
}

export function logout(): Promise<void> {
  return unwrap(api.POST("/api/v1/auth/logout", { body: {} })).then(() => undefined)
}

export function me(): Promise<User> {
  return unwrap(api.GET("/api/v1/auth/me"))
}
