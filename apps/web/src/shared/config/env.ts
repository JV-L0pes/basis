/** Runtime configuration, injected by Vite at build time. */
export const env = {
  apiUrl: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  appName: import.meta.env.VITE_APP_NAME ?? "Basis",
} as const
