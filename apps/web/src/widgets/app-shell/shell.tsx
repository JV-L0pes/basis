import {
  cn,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@basis/ui"
import { ArrowUpRight, CircleHalf } from "@basis/ui/icons"
import { Link, useNavigate } from "@tanstack/react-router"
import { logout } from "@/entities/session/api"
import { useSessionStore } from "@/entities/session/store"
import { env } from "@/shared/config/env"
import { useI18n } from "@/shared/i18n/provider"
import { LanguageSwitch, useThemeToggle } from "./controls"

const NAV = [
  { to: "/", key: "nav.dashboard" },
  { to: "/clientes", key: "nav.clients" },
  { to: "/carteiras", key: "nav.portfolios" },
  { to: "/mercado", key: "nav.markets" },
] as const

export function TopBar() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const user = useSessionStore((state) => state.user)
  const clear = useSessionStore((state) => state.clear)
  const toggleTheme = useThemeToggle()

  const handleLogout = async () => {
    try {
      await logout()
    } finally {
      clear()
      await navigate({ to: "/login" })
    }
  }

  return (
    <header className="bar stuck">
      <div className="shell bar-in">
        <div className="flex min-w-0 items-center gap-3">
          <Link to="/" className="mark" aria-label={t("app.name")}>
            BS
          </Link>
          <span className="late mono hidden md:inline">{t("app.tagline")}</span>
        </div>

        <nav
          className="mono flex min-w-0 items-center gap-5 overflow-x-auto md:gap-8"
          aria-label={t("nav.menu")}
        >
          {user
            ? NAV.map((item) => (
                <Link key={item.to} to={item.to} className="roll">
                  <span>
                    <i>{t(item.key)}</i>
                    <i aria-hidden="true">{t(item.key)}</i>
                  </span>
                </Link>
              ))
            : null}
        </nav>

        <div className="flex items-center gap-2">
          <LanguageSwitch className="hidden xs:inline-flex" />
          <button type="button" onClick={toggleTheme} className="sq" aria-label={t("nav.theme")}>
            <CircleHalf size={15} />
          </button>

          {user ? (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button type="button" className={cn("sq mono")} aria-label={user.display_name}>
                  {user.display_name.slice(0, 2).toUpperCase()}
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>{user.display_name}</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={() => void handleLogout()}>
                  <ArrowUpRight size={13} /> {t("nav.logout")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          ) : (
            <Link to="/login" className="plain">
              {t("auth.submit")}
            </Link>
          )}
        </div>
      </div>
    </header>
  )
}

export function AppFooter() {
  const { t } = useI18n()
  return (
    <footer className="foot">
      <div className="shell foot-grid">
        <div>
          <h4>{t("app.name")}</h4>
          <p className="foot-note">{t("footer.rights")}</p>
        </div>
        <div>
          <h4>{t("footer.notice")}</h4>
          <p className="foot-note">{t("footer.disclaimer")}</p>
        </div>
        <div>
          <h4>{t("footer.version")}</h4>
          <div className="flex flex-wrap items-baseline gap-x-6 gap-y-2">
            <span className="mono">Alpha · 0.1.0</span>
            <a
              className="foot-link mono"
              href={`${env.apiUrl}/docs`}
              target="_blank"
              rel="noreferrer"
            >
              {t("footer.api")}
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}
