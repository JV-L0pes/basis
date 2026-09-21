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
  Textarea,
  toast,
} from "@basis/ui"
import { zodResolver } from "@hookform/resolvers/zod"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { useInstruments } from "@/entities/instrument/api"
import { useRecordTransaction } from "@/entities/portfolio/api"
import { toProblem } from "@/shared/api/problem"
import { useI18n } from "@/shared/i18n/provider"

const KINDS = ["buy", "sell", "dividend", "interest", "fee"] as const

const schema = z.object({
  symbol: z.string().min(2, "common.required"),
  kind: z.enum(KINDS),
  trade_date: z.string().min(10, "common.required"),
  quantity: z.coerce.number().positive("common.required"),
  price: z.coerce.number().min(0, "common.required"),
  fees: z.coerce.number().min(0).optional(),
  notes: z.string().max(280).optional(),
})

type FormValues = z.infer<typeof schema>

export function RecordTransactionDialog({
  portfolioId,
  open,
  onOpenChange,
}: {
  portfolioId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { t } = useI18n()
  const instruments = useInstruments({})
  const record = useRecordTransaction(portfolioId)

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      symbol: "",
      kind: "buy",
      trade_date: new Date().toISOString().slice(0, 10),
      quantity: 1,
      price: 0,
      fees: 0,
      notes: "",
    },
  })

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      await record.mutateAsync({
        symbol: values.symbol,
        kind: values.kind,
        trade_date: values.trade_date,
        quantity: String(values.quantity),
        price: String(values.price),
        fees: values.fees ? String(values.fees) : undefined,
        notes: values.notes || undefined,
      })
      toast.success(t("portfolios.transactionRecorded"))
      form.reset({ ...form.getValues(), symbol: "", quantity: 1, price: 0, fees: 0, notes: "" })
      onOpenChange(false)
    } catch (error) {
      toast.error(toProblem(error).detail)
    }
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby={undefined} className="w-[min(94vw,36rem)]">
        <DialogHeader>
          <DialogTitle>{t("portfolios.newTransaction")}</DialogTitle>
          <DialogDescription>{t("portfolios.transactions")}</DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} noValidate className="form-grid two">
          <Field label={t("common.symbol")} htmlFor="tx-symbol" required>
            <Select
              value={form.watch("symbol")}
              onValueChange={(value) => form.setValue("symbol", value, { shouldValidate: true })}
            >
              <SelectTrigger id="tx-symbol">
                <SelectValue placeholder={t("markets.instruments")} />
              </SelectTrigger>
              <SelectContent>
                {(instruments.data?.items ?? []).map((instrument) => (
                  <SelectItem key={instrument.id} value={instrument.symbol}>
                    {instrument.symbol} · {instrument.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field label={t("common.type")} htmlFor="tx-kind">
            <Select
              value={form.watch("kind")}
              onValueChange={(value) => form.setValue("kind", value as FormValues["kind"])}
            >
              <SelectTrigger id="tx-kind">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {KINDS.map((kind) => (
                  <SelectItem key={kind} value={kind}>
                    {t(`transactionKind.${kind}` as "transactionKind.buy")}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field label={t("common.date")} htmlFor="tx-date" required>
            <Input id="tx-date" type="date" {...form.register("trade_date")} />
          </Field>

          <Field label={t("common.quantity")} htmlFor="tx-quantity" required>
            <Input
              id="tx-quantity"
              type="number"
              step="0.00000001"
              {...form.register("quantity")}
            />
          </Field>

          <Field label={t("common.price")} htmlFor="tx-price" required>
            <Input id="tx-price" type="number" step="0.01" {...form.register("price")} />
          </Field>

          <Field label={t("common.fees")} htmlFor="tx-fees" hint={t("common.optional")}>
            <Input id="tx-fees" type="number" step="0.01" {...form.register("fees")} />
          </Field>

          <Field
            label={t("common.notes")}
            htmlFor="tx-notes"
            className="md:col-span-2"
            hint={t("common.optional")}
          >
            <Textarea id="tx-notes" {...form.register("notes")} />
          </Field>

          <DialogFooter className="md:col-span-2">
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" loading={record.isPending}>
              {record.isPending ? t("common.saving") : t("common.create")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
