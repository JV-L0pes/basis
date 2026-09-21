import { useCallback, useEffect, useState } from "react"

export type Theme = "light" | "dark"

export const THEME_STORAGE_KEY = "basis-theme"

function readInitialTheme(): Theme {
  if (typeof document === "undefined") return "light"
  const fromDom = document.documentElement.dataset.theme
  if (fromDom === "dark" || fromDom === "light") return fromDom
  if (typeof window !== "undefined" && window.matchMedia) {
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"
  }
  return "light"
}

/**
 * Inline script to run before first paint. Prevents the wrong-theme flash:
 * with no stored preference it follows the OS, and it always leaves
 * `data-theme` set on `<html>`.
 *
 * Usage (framework-free, no `next/*`):
 *   <script dangerouslySetInnerHTML={{ __html: themeScript }} />
 */
export const themeScript = `(function(){try{var s=localStorage.getItem('${THEME_STORAGE_KEY}');var d=s?s==='dark':window.matchMedia('(prefers-color-scheme: dark)').matches;document.documentElement.dataset.theme=d?'dark':'light';}catch(e){document.documentElement.dataset.theme='light';}})();`

/**
 * Reads and writes the Ink theme. The DOM (`data-theme` on `<html>`) is the
 * source of truth; localStorage only remembers the choice. `themeScript`
 * must have run once to make the first render FOUC-safe.
 */
export function useTheme() {
  const [theme, setThemeState] = useState<Theme>(readInitialTheme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, theme)
    } catch {
      /* storage indisponivel; o DOM ja esta correto */
    }
  }, [theme])

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next)
  }, [])

  const toggle = useCallback(() => {
    setThemeState((current) => (current === "dark" ? "light" : "dark"))
  }, [])

  return { theme, setTheme, toggle }
}
