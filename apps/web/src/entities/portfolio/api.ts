import type { components } from "@basis/contracts"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api, unwrap } from "@/shared/api/client"

export type Portfolio = components["schemas"]["PortfolioResponse"]
export type PortfolioList = components["schemas"]["PortfolioListResponse"]
export type Transaction = components["schemas"]["TransactionResponse"]
export type PortfolioValuation = components["schemas"]["PortfolioValuationResponse"]
export type Performance = components["schemas"]["PerformanceResponse"]
export type AllocationAnalysis = components["schemas"]["AllocationAnalysisResponse"]

export const portfolioKeys = {
  all: ["portfolios"] as const,
  list: (filters: { clientId?: string } = {}) => ["portfolios", "list", filters] as const,
  detail: (id: string) => ["portfolios", "detail", id] as const,
  transactions: (id: string) => ["portfolios", id, "transactions"] as const,
  performance: (id: string, period: number) => ["portfolios", id, "performance", period] as const,
  allocation: (id: string) => ["portfolios", id, "allocation"] as const,
}

export function usePortfolios(filters: { clientId?: string } = {}) {
  return useQuery({
    queryKey: portfolioKeys.list(filters),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/portfolios", {
          params: { query: { client_id: filters.clientId, limit: 50 } },
        }),
      ),
  })
}

export function usePortfolio(id: string) {
  return useQuery({
    queryKey: portfolioKeys.detail(id),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/portfolios/{portfolio_id}", {
          params: { path: { portfolio_id: id } },
        }),
      ),
    enabled: Boolean(id),
  })
}

export function useTransactions(id: string) {
  return useQuery({
    queryKey: portfolioKeys.transactions(id),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/portfolios/{portfolio_id}/transactions", {
          params: { path: { portfolio_id: id } },
        }),
      ),
    enabled: Boolean(id),
  })
}

export function usePerformance(id: string, periodDays: number) {
  const end = new Date()
  const start = new Date(end.getTime() - periodDays * 24 * 60 * 60 * 1000)
  const iso = (date: Date) => date.toISOString().slice(0, 10)
  return useQuery({
    queryKey: portfolioKeys.performance(id, periodDays),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/analytics/portfolios/{portfolio_id}/performance", {
          params: {
            path: { portfolio_id: id },
            query: { start: iso(start), end: iso(end) },
          },
        }),
      ),
    enabled: Boolean(id),
  })
}

export function useAllocation(id: string) {
  return useQuery({
    queryKey: portfolioKeys.allocation(id),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/analytics/portfolios/{portfolio_id}/allocation", {
          params: { path: { portfolio_id: id } },
        }),
      ),
    enabled: Boolean(id),
  })
}

export function useOpenPortfolio() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: { client_id: string; name: string; base_currency: string }) =>
      unwrap(api.POST("/api/v1/portfolios", { body })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: portfolioKeys.all }),
  })
}

export function useRecordTransaction(portfolioId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: components["schemas"]["RecordTransactionRequest"]) =>
      unwrap(
        api.POST("/api/v1/portfolios/{portfolio_id}/transactions", {
          params: { path: { portfolio_id: portfolioId } },
          body,
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: portfolioKeys.all }),
  })
}

export function useSetTargets(portfolioId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (targets: { asset_class: string; weight_bps: number }[]) =>
      unwrap(
        api.PUT("/api/v1/portfolios/{portfolio_id}/targets", {
          params: { path: { portfolio_id: portfolioId } },
          body: { targets: targets as components["schemas"]["TargetWeightRequest"][] },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: portfolioKeys.all }),
  })
}
