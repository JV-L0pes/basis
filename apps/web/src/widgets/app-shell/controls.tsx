import { cn } from "@basis/ui"
import { useCallback } from "react"

import { useI18n } from "@/shared/i18n/provider"

export interface LanguageSwitchProps {
  className?: string
}

export function LanguageSwitch({ className }: LanguageSwitchProps) {
  const { language, setLanguage, t } = useI18n()
  return (
    // biome-ignore lint/a11y/useSemanticElements: toggle group, not a form fieldset
    <div className={cn("seg", className)} role="group" aria-label={t("lang.label")}>
      <button
        type="button"
        onClick={() => {
          setLanguage("pt")
        }}
        aria-pressed={language === "pt"}
      >
        {t("lang.pt")}
      </button>
      <button
        type="button"
        onClick={() => {
          setLanguage("en")
        }}
        aria-pressed={language === "en"}
      >
        {t("lang.en")}
      </button>
    </div>
  )
}

export function useThemeToggle() {
  const toggle = useCallback(() => {
    const root = document.documentElement
    const next = root.dataset.theme === "dark" ? "light" : "dark"
    root.dataset.theme = next
    try {
      localStorage.setItem("basis-theme", next)
    } catch {
      /* storage unavailable */
    }
  }, [])
  return toggle
}
