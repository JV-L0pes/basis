import { useReveal } from "@basis/ui"

import { LoginForm } from "@/features/auth/login-form"
import { useI18n } from "@/shared/i18n/provider"

export function LoginPage() {
  const { t } = useI18n()
  useReveal()

  return (
    <main className="shell flex flex-1 items-center py-16">
      <div className="grid w-full gap-12 md:grid-cols-2">
        <div className="hidden flex-col justify-between gap-10 border-r border-rule pr-12 md:flex">
          <div>
            <h1 className="giant wide">
              <span className="line">
                <span>{t("app.name")}</span>
              </span>
            </h1>
            <p className="lede mt-8">{t("app.description")}</p>
          </div>
          <span className="mono text-ash">{t("app.tagline")}</span>
        </div>

        <div className="flex flex-col justify-center">
          <div className="sec-head">
            <span className="kicker">{t("auth.subtitle")}</span>
            <h2 className="text-4xl">{t("auth.title")}</h2>
          </div>
          <LoginForm />
          <p className="mt-6 text-xs text-ash">{t("auth.firstUser")}</p>
        </div>
      </div>
    </main>
  )
}
