import { RouterProvider } from "@tanstack/react-router"
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"

import { AppProviders } from "@/app/providers"
import { router } from "@/app/router"
import "@/app/styles.css"

const container = document.getElementById("root")
if (!container) throw new Error("Root container not found")

createRoot(container).render(
  <StrictMode>
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  </StrictMode>,
)
