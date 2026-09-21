import { LoginForm } from "@/features/auth/login-form"
import { useI18n } from "@/shared/i18n/provider"
import { LanguageSwitch } from "@/widgets/app-shell/controls"

export function LoginPage() {
  const { t } = useI18n()
  return (
    <main className="shell flex flex-1 items-center justify-center py-16">
      <div className="grid w-full max-w-5xl gap-12 md:grid-cols-2">
        <div className="hidden flex-col justify-between gap-8 border-r border-rule pr-12 md:flex">
          <div>
            <div className="mark mb-6">BS</div>
            <h1 className="giant wide">
              <span className="line">
                <span>{t("app.name")}</span>
              </span>
            </h1>
            <p className="lede mt-6">{t("app.description")}</p>
          </div>
          <div className="flex items-center justify-between">
            <span className="mono text-ash">{t("app.tagline")}</span>
            <LanguageSwitch />
          </div>
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
