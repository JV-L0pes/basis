import type { components } from "@basis/contracts"
import { useQuery } from "@tanstack/react-query"

import { api, unwrap } from "@/shared/api/client"

const marketKeys = {
  instruments: (query?: string, assetClass?: string) =>
    ["instruments", { query, assetClass }] as const,
  instrument: (symbol: string) => ["instruments", symbol] as const,
  quote: (symbol: string) => ["instruments", symbol, "quote"] as const,
  history: (symbol: string, days: number) => ["instruments", symbol, "history", days] as const,
  macro: (code: string) => ["macro", code] as const,
  overview: ["market", "overview"] as const,
}

export function useInstruments(filters: { query?: string; assetClass?: string } = {}) {
  return useQuery({
    queryKey: marketKeys.instruments(filters.query, filters.assetClass),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/instruments", {
          params: {
            query: {
              query: filters.query,
              asset_class: filters.assetClass as components["schemas"]["AssetClass"] | undefined,
              limit: 50,
            },
          },
        }),
      ),
  })
}
export function useInstrument(symbol: string) {
  return useQuery({
    queryKey: marketKeys.instrument(symbol),
    queryFn: () =>
      unwrap(api.GET("/api/v1/instruments/{symbol}", { params: { path: { symbol } } })),
    enabled: Boolean(symbol),
  })
}

export function useQuote(symbol: string) {
  return useQuery({
    queryKey: marketKeys.quote(symbol),
    queryFn: () =>
      unwrap(api.GET("/api/v1/instruments/{symbol}/quote", { params: { path: { symbol } } })),
    enabled: Boolean(symbol),
    refetchInterval: 60_000,
  })
}

export function useHistory(symbol: string, days = 90) {
  const end = new Date()
  const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000)
  const iso = (date: Date) => date.toISOString().slice(0, 10)
  return useQuery({
    queryKey: marketKeys.history(symbol, days),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/instruments/{symbol}/history", {
          params: {
            path: { symbol },
            query: { start: iso(start), end: iso(end) },
          },
        }),
      ),
    enabled: Boolean(symbol),
  })
}

export function useMarketOverview() {
  return useQuery({
    queryKey: marketKeys.overview,
    queryFn: () => unwrap(api.GET("/api/v1/market/overview")),
    staleTime: 60_000,
  })
}

export function useBookOverview() {
  return useQuery({
    queryKey: ["analytics", "book"],
    queryFn: () => unwrap(api.GET("/api/v1/analytics/book")),
    staleTime: 60_000,
  })
}
