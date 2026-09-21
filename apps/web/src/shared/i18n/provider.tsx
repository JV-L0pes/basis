import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react"

import { dictionaries, type Language, type MessageKey } from "./messages"

const STORAGE_KEY = "basis-lang"

type I18nValue = {
  language: Language
  locale: string
  setLanguage: (language: Language) => void
  t: (key: MessageKey, params?: Record<string, string | number>) => string
}

const I18nContext = createContext<I18nValue | null>(null)

function readInitialLanguage(): Language {
  if (typeof localStorage === "undefined") return "pt"
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === "pt" || stored === "en") return stored
  return navigator.language?.toLowerCase().startsWith("en") ? "en" : "pt"
}

function interpolate(template: string, params?: Record<string, string | number>): string {
  if (!params) return template
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in params ? String(params[key]) : match,
  )
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(readInitialLanguage)

  useEffect(() => {
    document.documentElement.lang = language === "pt" ? "pt-BR" : "en"
    try {
      localStorage.setItem(STORAGE_KEY, language)
    } catch {
      /* storage unavailable — the language still applies for this session */
    }
  }, [language])

  const setLanguage = useCallback((next: Language) => setLanguageState(next), [])

  const value = useMemo<I18nValue>(
    () => ({
      language,
      locale: language === "pt" ? "pt-BR" : "en-US",
      setLanguage,
      t: (key, params) => interpolate(dictionaries[language][key], params),
    }),
    [language, setLanguage],
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nValue {
  const value = useContext(I18nContext)
  if (!value) throw new Error("useI18n must be used inside I18nProvider")
  return value
}

export function useT() {
  return useI18n().t
}
