import { useCallback, useSyncExternalStore } from "react"

/**
 * Subscribes to a CSS media query. SSR-safe: the server snapshot is always
 * `false`, and the first client render subscribes before paint.
 */
export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onStoreChange: () => void) => {
      if (typeof window === "undefined" || !window.matchMedia) return () => {}
      const list = window.matchMedia(query)
      list.addEventListener("change", onStoreChange)
      return () => list.removeEventListener("change", onStoreChange)
    },
    [query],
  )

  const getSnapshot = useCallback(() => {
    if (typeof window === "undefined" || !window.matchMedia) return false
    return window.matchMedia(query).matches
  }, [query])

  return useSyncExternalStore(subscribe, getSnapshot, () => false)
}

/** `< 960px`, the Ink shell breakpoint used by the top bar. */
export function useIsMobile() {
  return useMediaQuery("(max-width: 959px)")
}

export function usePrefersReducedMotion() {
  return useMediaQuery("(prefers-reduced-motion: reduce)")
}
