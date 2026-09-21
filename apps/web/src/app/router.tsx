import {
  createRootRoute,
  createRoute,
  createRouter,
  Link,
  Outlet,
  redirect,
} from "@tanstack/react-router"
import { useSessionStore } from "@/entities/session/store"
import { ClientsPage } from "@/pages/clients/page"
import { DashboardPage } from "@/pages/dashboard/page"
import { InstrumentPage } from "@/pages/instrument/page"
import { LoginPage } from "@/pages/login/page"
import { MarketsPage } from "@/pages/markets/page"
import { PortfolioPage } from "@/pages/portfolio/page"
import { PortfoliosPage } from "@/pages/portfolios/page"
import { sessionBootstrap } from "@/shared/session-bootstrap"
import { LanguageSwitch, useThemeToggle } from "@/widgets/app-shell/controls"
import { TopBar } from "@/widgets/app-shell/shell"

function NotFound() {
  const toggleTheme = useThemeToggle()
  return (
    <main className="shell page">
      <div className="sec-head">
        <span className="kicker">404</span>
        <h2 className="text-6xl">Página não encontrada</h2>
      </div>
      <div className="flex items-center gap-4">
        <Link to="/" className="pill">
          Voltar ao painel
        </Link>
        <button type="button" className="plain" onClick={toggleTheme}>
          Alternar tema
        </button>
        <LanguageSwitch />
      </div>
    </main>
  )
}

function AppLayout() {
  return (
    <>
      <TopBar />
      <Outlet />
    </>
  )
}

const rootRoute = createRootRoute({
  component: AppLayout,
  notFoundComponent: NotFound,
  beforeLoad: async ({ location }) => {
    await sessionBootstrap.promise
    const authenticated = useSessionStore.getState().isAuthenticated()
    if (!authenticated && location.pathname !== "/login") {
      throw redirect({ to: "/login" })
    }
  },
})

const dashboardRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: DashboardPage,
})

const clientsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/clientes",
  component: ClientsPage,
})

const portfoliosRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/carteiras",
  component: PortfoliosPage,
})

const portfolioRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/carteiras/$portfolioId",
  component: PortfolioPage,
})

const marketsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/mercado",
  component: MarketsPage,
})

const instrumentRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/mercado/$symbol",
  component: InstrumentPage,
})

const loginRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  component: LoginPage,
})

const routeTree = rootRoute.addChildren([
  dashboardRoute,
  clientsRoute,
  portfoliosRoute,
  portfolioRoute,
  marketsRoute,
  instrumentRoute,
  loginRoute,
])

export const router = createRouter({
  routeTree,
  defaultPreload: "intent",
  scrollRestoration: true,
})

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router
  }
}
