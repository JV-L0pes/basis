import {
  cn,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Sheet,
  SheetClose,
  SheetContent,
} from "@basis/ui"
import { ArrowUpRight, CircleHalf } from "@basis/ui/icons"
import { useNavigate } from "@tanstack/react-router"
import { useState } from "react"

import { logout } from "@/entities/session/api"
import { useSessionStore } from "@/entities/session/store"
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
  const [menuOpen, setMenuOpen] = useState(false)

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
          <a href="/" className="mark" aria-label={t("app.name")}>
            BS
          </a>
          <span className="late mono">{t("app.tagline")}</span>
        </div>

        <nav className="mono hidden items-center gap-8 md:flex" aria-label={t("nav.menu")}>
          {NAV.map((item) => (
            <a key={item.to} href={item.to} className="roll">
              <span>
                <i>{t(item.key)}</i>
                <i aria-hidden="true">{t(item.key)}</i>
              </span>
            </a>
          ))}
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
            <a href="/login" className="plain">
              {t("auth.submit")}
            </a>
          )}

          <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
            <button
              type="button"
              className="sq md:hidden"
              aria-label={t("nav.menu")}
              onClick={() => setMenuOpen(true)}
            >
              ≡
            </button>
            <SheetContent side="right" aria-describedby={undefined}>
              <div className="mb-8 flex items-center justify-between">
                <span className="mono">{t("nav.menu")}</span>
                <SheetClose className="sq" aria-label={t("common.close")}>
                  ×
                </SheetClose>
              </div>
              <nav className="flex flex-col gap-5">
                {NAV.map((item) => (
                  <a
                    key={item.to}
                    href={item.to}
                    className="text-2xl font-extrabold tracking-[-0.03em]"
                    onClick={() => setMenuOpen(false)}
                  >
                    {t(item.key)}
                  </a>
                ))}
              </nav>
              <div className="mt-8">
                <LanguageSwitch />
              </div>
            </SheetContent>
          </Sheet>
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
          <div className="mark mb-3">BS</div>
          <p className="max-w-[34ch] text-sm">{t("footer.rights")}</p>
        </div>
        <div>
          <h4>{t("footer.disclaimer")}</h4>
        </div>
        <div>
          <h4>{t("app.tagline")}</h4>
          <p className="mono">Alpha · 0.1.0</p>
        </div>
      </div>
    </footer>
  )
}
