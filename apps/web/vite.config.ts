import { fileURLToPath } from "node:url"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vitest/config"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // A single .env at the repository root drives the API and the web app.
  envDir: fileURLToPath(new URL("../..", import.meta.url)),
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    // 5173 is taken by another local project on this machine.
    port: 5174,
    strictPort: true,
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
})
