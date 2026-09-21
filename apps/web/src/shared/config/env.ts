/** Runtime configuration, injected by Vite at build time. */

const viteEnv = import.meta.env as Record<string, string | undefined>

export const env = {
  apiUrl: viteEnv.VITE_API_URL ?? "http://localhost:8000",
  appName: viteEnv.VITE_APP_NAME ?? "Basis",
} as const
