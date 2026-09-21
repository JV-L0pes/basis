import { useEffect } from "react"

export interface UseRevealOptions {
  /** Selector of the elements to reveal. */
  selector?: string
  /** IntersectionObserver threshold. */
  threshold?: number
  /** IntersectionObserver rootMargin. */
  rootMargin?: string
  /** Safety net in ms: reveals everything if the observer never fires. */
  safetyTimeout?: number
}

/**
 * Reveals `.fade` and `.line` elements in cascade as they enter the
 * viewport. Port of the portfolio hook with the same safety net: a 2s timer
 * guarantees content is never left invisible. `prefers-reduced-motion`
 * reveals everything immediately.
 */
export function useReveal({
  selector = ".fade, .line, h1, h2",
  threshold = 0.12,
  rootMargin = "0px 0px -6% 0px",
  safetyTimeout = 2000,
}: UseRevealOptions = {}) {
  useEffect(() => {
    const targets = document.querySelectorAll<HTMLElement>(selector)
    const showAll = () => {
      targets.forEach((el) => {
        el.classList.add("on")
      })
      document.querySelectorAll<HTMLElement>(".line").forEach((el) => {
        el.classList.add("on")
      })
    }

    if (
      window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
      !("IntersectionObserver" in window)
    ) {
      showAll()
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return
          const el = entry.target as HTMLElement
          const siblings = Array.from(el.parentElement?.children ?? []).filter(
            (n) => n.classList.contains("fade") || n.tagName === "H1" || n.tagName === "H2",
          )
          const index = siblings.indexOf(el)
          const delay = Math.min(Math.max(index, 0), 5) * 90
          el.style.transitionDelay = `${delay}ms`
          el.querySelectorAll<HTMLElement>(".line > span").forEach((span, i) => {
            span.style.transitionDelay = `${delay + i * 110}ms`
          })
          el.classList.add("on")
          observer.unobserve(el)
        })
      },
      { threshold, rootMargin },
    )

    targets.forEach((el) => {
      observer.observe(el)
    })
    const safety = window.setTimeout(showAll, safetyTimeout)

    return () => {
      observer.disconnect()
      window.clearTimeout(safety)
    }
  }, [selector, threshold, rootMargin, safetyTimeout])
}
