import type { AnchorHTMLAttributes, ReactNode } from "react"

/**
 * Deterministic replacement for `@tanstack/react-router` used only in tests
 * (see vitest.config.ts). Tests assert page behaviour, not routing: `Link`
 * becomes an anchor and params/search are injected via `setTestRoute`.
 */

let testParams: Record<string, string> = {}
let testSearch: Record<string, unknown> = {}

export function setTestRoute(route: {
  params?: Record<string, string>
  search?: Record<string, unknown>
}): void {
  testParams = route.params ?? {}
  testSearch = route.search ?? {}
}

type LinkProps = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "href"> & {
  to: string
  params?: Record<string, string>
  search?: Record<string, unknown>
  children?: ReactNode
}

function hrefOf(to: string, params?: Record<string, string>, search?: Record<string, unknown>) {
  const path = params
    ? Object.entries(params).reduce((acc, [key, value]) => acc.replace(`$${key}`, value), to)
    : to
  if (!search) return path
  const query = new URLSearchParams(
    Object.entries(search).map(([key, value]) => [key, String(value)]),
  )
  return `${path}?${query.toString()}`
}

export function Link({ to, params, search, children, ...rest }: LinkProps) {
  return (
    <a href={hrefOf(to, params, search)} {...rest}>
      {children}
    </a>
  )
}

export function useParams() {
  return testParams
}

export function useSearch() {
  return testSearch
}

export function useNavigate() {
  return () => Promise.resolve()
}

export function useRouterState() {
  return { location: { pathname: "/" } }
}

export function Outlet() {
  return null
}

export function redirect(options: unknown) {
  return options
}
