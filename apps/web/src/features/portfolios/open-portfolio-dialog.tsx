import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Field,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  toast,
} from "@basis/ui"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm, useWatch } from "react-hook-form"
import { z } from "zod"

import { useClients } from "@/entities/client/api"
import { useOpenPortfolio } from "@/entities/portfolio/api"
import { toProblem } from "@/shared/api/problem"
import { useI18n } from "@/shared/i18n/provider"

const schema = z.object({
  clientId: z.string().min(1, "common.required"),
  name: z.string().min(2, "common.required").max(80),
  baseCurrency: z.string().min(3).max(5),
})

type FormValues = z.infer<typeof schema>

export function OpenPortfolioDialog({
  open,
  onOpenChange,
  defaultClientId,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultClientId?: string
}) {
  const { t } = useI18n()
  const clients = useClients({ limit: 100 })
  const openPortfolio = useOpenPortfolio()

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { clientId: defaultClientId ?? "", name: "", baseCurrency: "BRL" },
  })
  const clientId = useWatch({ control: form.control, name: "clientId" })
  const baseCurrency = useWatch({ control: form.control, name: "baseCurrency" })

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await openPortfolio.mutateAsync({
        client_id: values.clientId,
        name: values.name,
        base_currency: values.baseCurrency,
      })
      toast.success(t("portfolios.opened"))
      form.reset({ clientId: values.clientId, name: "", baseCurrency: "BRL" })
      onOpenChange(false)
    } catch (error) {
      toast.error(toProblem(error).detail)
    }
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby={undefined}>
        <DialogHeader>
          <DialogTitle>{t("portfolios.new")}</DialogTitle>
          <DialogDescription>{t("portfolios.subtitle")}</DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} noValidate className="flex flex-col gap-4">
          <Field label={t("portfolios.client")} htmlFor="portfolio-client" required>
            <Select
              value={clientId}
              onValueChange={(value) => form.setValue("clientId", value, { shouldValidate: true })}
            >
              <SelectTrigger id="portfolio-client">
                <SelectValue placeholder={t("portfolios.client")} />
              </SelectTrigger>
              <SelectContent>
                {(clients.data?.items ?? []).map((client) => (
                  <SelectItem key={client.id} value={client.id}>
                    {client.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field
            label={t("portfolios.name")}
            htmlFor="portfolio-name"
            required
            error={form.formState.errors.name ? t("common.required") : undefined}
          >
            <Input id="portfolio-name" {...form.register("name")} />
          </Field>

          <Field label={t("portfolios.currency")} htmlFor="portfolio-currency">
            <Select
              value={baseCurrency}
              onValueChange={(value) => form.setValue("baseCurrency", value)}
            >
              <SelectTrigger id="portfolio-currency">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="BRL">BRL</SelectItem>
                <SelectItem value="USD">USD</SelectItem>
              </SelectContent>
            </Select>
          </Field>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" loading={openPortfolio.isPending}>
              {openPortfolio.isPending ? t("common.saving") : t("portfolios.open")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
