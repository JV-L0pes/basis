import type { components } from "@basis/contracts"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api, unwrap } from "@/shared/api/client"

export type Client = components["schemas"]["ClientResponse"]
export type ClientList = components["schemas"]["ClientListResponse"]
export type ClientStatus = "active" | "archived"

export type ClientFilters = {
  query?: string
  status?: ClientStatus
  limit?: number
  cursor?: string | null
}

export const clientsKeys = {
  all: ["clients"] as const,
  list: (filters: ClientFilters) => ["clients", "list", filters] as const,
  detail: (id: string) => ["clients", "detail", id] as const,
}

export function useClients(filters: ClientFilters = {}) {
  return useQuery({
    queryKey: clientsKeys.list(filters),
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/clients", {
          params: {
            query: {
              query: filters.query || undefined,
              status: filters.status,
              limit: filters.limit ?? 20,
              cursor: filters.cursor ?? undefined,
            },
          },
        }),
      ),
  })
}

export function useClient(id: string) {
  return useQuery({
    queryKey: clientsKeys.detail(id),
    queryFn: () =>
      unwrap(api.GET("/api/v1/clients/{client_id}", { params: { path: { client_id: id } } })),
    enabled: Boolean(id),
  })
}

export type RegisterClientInput = {
  name: string
  email: string
  tax_id: string
  notes?: string
  suitability_answers?: number[]
}

export function useCreateClient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: RegisterClientInput) =>
      unwrap(api.POST("/api/v1/clients", { body: input })),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clientsKeys.all }),
  })
}

export function useUpdateClient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; name?: string; email?: string; notes?: string }) =>
      unwrap(
        api.PATCH("/api/v1/clients/{client_id}", {
          params: { path: { client_id: id } },
          body,
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clientsKeys.all }),
  })
}

export function useArchiveClient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.POST("/api/v1/clients/{client_id}/archive", {
          params: { path: { client_id: id } },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clientsKeys.all }),
  })
}

export function useReactivateClient() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      unwrap(
        api.POST("/api/v1/clients/{client_id}/reactivate", {
          params: { path: { client_id: id } },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clientsKeys.all }),
  })
}

export function useAssessSuitability() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, answers }: { id: string; answers: number[] }) =>
      unwrap(
        api.POST("/api/v1/clients/{client_id}/suitability", {
          params: { path: { client_id: id } },
          body: { answers },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: clientsKeys.all }),
  })
}
