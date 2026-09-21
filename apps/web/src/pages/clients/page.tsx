import {
  Badge,
  Button,
  Input,
  Ledger,
  LedgerBody,
  LedgerCell,
  LedgerHead,
  LedgerHeadCell,
  LedgerRow,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  toast,
} from "@basis/ui"
import { useState } from "react"

import {
  type Client,
  useArchiveClient,
  useClients,
  useReactivateClient,
} from "@/entities/client/api"
import { ClientFormDialog } from "@/features/clients/client-form-dialog"
import { SuitabilityDialog } from "@/features/clients/suitability-dialog"
import { toProblem } from "@/shared/api/problem"
import { useI18n } from "@/shared/i18n/provider"
import { AsyncState, PageHeader } from "@/shared/ui/primitives"

function suitabilityVariant(profile: string) {
  if (profile === "aggressive") return "negative" as const
  if (profile === "moderate") return "neutral" as const
  return "muted" as const
}

export function ClientsPage() {
  const { t } = useI18n()
  const [query, setQuery] = useState("")
  const [status, setStatus] = useState<"all" | "active" | "archived">("all")
  const [cursor, setCursor] = useState<string | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<Client | undefined>(undefined)
  const [assessing, setAssessing] = useState<Client | undefined>(undefined)

  const clients = useClients({
    query: query || undefined,
    status: status === "all" ? undefined : status,
    cursor,
  })
  const archive = useArchiveClient()
  const reactivate = useReactivateClient()

  const items = clients.data?.items ?? []
  const nextCursor = clients.data?.next_cursor ?? null

  const toggleStatus = async (client: Client) => {
    try {
      if (client.status === "active") {
        await archive.mutateAsync(client.id)
        toast.success(t("clients.archived"))
      } else {
        await reactivate.mutateAsync(client.id)
        toast.success(t("clients.reactivated"))
      }
    } catch (error) {
      toast.error(toProblem(error).detail)
    }
  }

  return (
    <main className="shell page">
      <PageHeader
        kicker={t("clients.kicker")}
        title={t("clients.title")}
        subtitle={t("clients.subtitle")}
        actions={
          <Button
            onClick={() => {
              setEditing(undefined)
              setFormOpen(true)
            }}
          >
            {t("clients.new")}
          </Button>
        }
      />

      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[16rem] flex-1">
          <Input
            value={query}
            onChange={(event) => {
              setQuery(event.target.value)
              setCursor(null)
            }}
            placeholder={t("clients.searchPlaceholder")}
            aria-label={t("common.search")}
          />
        </div>
        <div className="w-44">
          <Select
            value={status}
            onValueChange={(value) => {
              setStatus(value as typeof status)
              setCursor(null)
            }}
          >
            <SelectTrigger aria-label={t("clients.filterStatus")}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t("common.total")}</SelectItem>
              <SelectItem value="active">{t("status.active")}</SelectItem>
              <SelectItem value="archived">{t("status.archived")}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <AsyncState
        isLoading={clients.isLoading}
        error={clients.error}
        isEmpty={items.length === 0}
        emptyLabel={t("clients.empty")}
      >
        <Ledger>
          <LedgerHead>
            <LedgerRow>
              <LedgerHeadCell>{t("clients.name")}</LedgerHeadCell>
              <LedgerHeadCell>{t("clients.taxId")}</LedgerHeadCell>
              <LedgerHeadCell>{t("clients.suitability")}</LedgerHeadCell>
              <LedgerHeadCell>{t("clients.status")}</LedgerHeadCell>
              <LedgerHeadCell numeric>—</LedgerHeadCell>
            </LedgerRow>
          </LedgerHead>
          <LedgerBody>
            {items.map((client) => (
              <LedgerRow key={client.id}>
                <LedgerCell>
                  <div className="flex flex-col">
                    <span className="font-semibold">{client.name}</span>
                    <span className="text-xs text-ash">{client.email}</span>
                  </div>
                </LedgerCell>
                <LedgerCell>
                  <span className="mono">{client.tax_id_masked}</span>
                </LedgerCell>
                <LedgerCell>
                  <span className="flex items-center gap-2">
                    <Badge variant={suitabilityVariant(client.suitability)}>
                      {t(`suitability.${client.suitability}` as "suitability.moderate")}
                    </Badge>
                    <span className="mono text-ash">{client.suitability_score}</span>
                  </span>
                </LedgerCell>
                <LedgerCell>
                  <Badge variant={client.status === "active" ? "positive" : "muted"}>
                    {t(`status.${client.status}` as "status.active")}
                  </Badge>
                </LedgerCell>
                <LedgerCell numeric>
                  <span className="flex justify-end gap-3">
                    <a className="plain" href={`/carteiras?clientId=${client.id}`}>
                      {t("common.view")}
                    </a>
                    <button
                      type="button"
                      className="plain"
                      onClick={() => {
                        setEditing(client)
                        setFormOpen(true)
                      }}
                    >
                      {t("common.edit")}
                    </button>
                    <button
                      type="button"
                      className="plain"
                      onClick={() => {
                        setAssessing(client)
                      }}
                    >
                      {t("clients.suitability")}
                    </button>
                    <button
                      type="button"
                      className="plain"
                      onClick={() => void toggleStatus(client)}
                      disabled={archive.isPending || reactivate.isPending}
                    >
                      {client.status === "active" ? t("common.archive") : t("common.reactivate")}
                    </button>
                  </span>
                </LedgerCell>
              </LedgerRow>
            ))}
          </LedgerBody>
        </Ledger>

        <div className="mt-4 flex items-center justify-between">
          <span className="mono text-ash">
            {t("clients.subtitle")} · {items.length}
          </span>
          {nextCursor ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCursor(nextCursor)}
              loading={clients.isFetching}
            >
              {t("common.more")}
            </Button>
          ) : null}
        </div>
      </AsyncState>

      <ClientFormDialog
        open={formOpen}
        onOpenChange={(open) => {
          setFormOpen(open)
          if (!open) setEditing(undefined)
        }}
        client={editing}
      />
      {assessing ? (
        <SuitabilityDialog
          client={assessing}
          open={true}
          onOpenChange={(open) => {
            if (!open) setAssessing(undefined)
          }}
        />
      ) : null}
    </main>
  )
}
