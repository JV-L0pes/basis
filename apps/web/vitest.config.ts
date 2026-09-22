import { fileURLToPath } from "node:url"
import { defineConfig } from "vitest/config"

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      // Pages use Link/useParams; tests get a deterministic stub so they can
      // focus on page behaviour without booting the router.
      "@tanstack/react-router": fileURLToPath(
        new URL("./src/test/router-stub.tsx", import.meta.url),
      ),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/setup-tests.ts"],
  },
})
