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
import { useForm, useWatch } from "react-hook-form"
import { z } from "zod"

import {
  type Client,
  type RegisterClientInput,
  useCreateClient,
  useUpdateClient,
} from "@/entities/client/api"
import { toProblem } from "@/shared/api/problem"
import { useI18n } from "@/shared/i18n/provider"

const schema = z.object({
  name: z.string().min(2, "common.required").max(120),
  email: z.email("common.required").max(254),
  tax_id: z.string().min(11, "common.required").max(18),
  notes: z.string().max(500).optional(),
  profile: z.enum(["conservative", "moderate", "aggressive", "questionnaire"]),
})

type FormValues = z.infer<typeof schema>

const ANSWER_SETS: Record<string, number[]> = {
  conservative: [0, 1, 1, 0, 1],
  moderate: [2, 2, 2, 2, 2],
  aggressive: [4, 4, 3, 4, 4],
}

export function ClientFormDialog({
  open,
  onOpenChange,
  client,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** When provided the dialog edits that client instead of creating one. */
  client?: Client
}) {
  const { t } = useI18n()
  const createClient = useCreateClient()
  const updateClient = useUpdateClient()
  const isEdit = client !== undefined

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    values: {
      name: client?.name ?? "",
      email: client?.email ?? "",
      tax_id: client?.tax_id_masked ?? "",
      notes: client?.notes ?? "",
      profile: "questionnaire",
    },
  })

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      if (isEdit) {
        await updateClient.mutateAsync({
          id: client.id,
          name: values.name,
          email: values.email,
          notes: values.notes ?? undefined,
        })
        toast.success(t("clients.updated"))
      } else {
        const answers = values.profile === "questionnaire" ? undefined : ANSWER_SETS[values.profile]
        const payload: RegisterClientInput = {
          name: values.name,
          email: values.email,
          tax_id: values.tax_id,
          notes: values.notes ?? undefined,
          suitability_answers: answers,
        }
        await createClient.mutateAsync(payload)
        toast.success(t("clients.created"))
        form.reset()
      }
      onOpenChange(false)
    } catch (error) {
      form.setError("root", { message: toProblem(error).detail })
    }
  })

  const profile = useWatch({ control: form.control, name: "profile" })
  const errors = form.formState.errors
  const isPending = createClient.isPending || updateClient.isPending
  const submitLabel = isEdit ? t("common.save") : t("common.create")

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby={undefined}>
        <DialogHeader>
          <DialogTitle>{isEdit ? t("common.edit") : t("clients.new")}</DialogTitle>
          <DialogDescription>{t("clients.subtitle")}</DialogDescription>
        </DialogHeader>

        <form onSubmit={onSubmit} noValidate className="form-grid two">
          <Field
            label={t("clients.name")}
            htmlFor="client-name"
            required
            error={errors.name ? t("common.required") : undefined}
          >
            <Input id="client-name" {...form.register("name")} />
          </Field>
          <Field
            label={t("clients.email")}
            htmlFor="client-email"
            required
            error={errors.email ? t("common.required") : undefined}
          >
            <Input id="client-email" type="email" {...form.register("email")} />
          </Field>
          <Field
            label={t("clients.taxId")}
            htmlFor="client-tax"
            required
            error={errors.tax_id ? t("common.required") : undefined}
            hint={isEdit ? t("clients.taxId") : undefined}
          >
            <Input
              id="client-tax"
              placeholder="000.000.000-00"
              disabled={isEdit}
              {...form.register("tax_id")}
            />
          </Field>
          {isEdit ? null : (
            <Field label={t("clients.suitability")} htmlFor="client-profile">
              <Select
                value={profile}
                onValueChange={(value) => form.setValue("profile", value as FormValues["profile"])}
              >
                <SelectTrigger id="client-profile">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="questionnaire">{t("clients.answers")}</SelectItem>
                  <SelectItem value="conservative">{t("suitability.conservative")}</SelectItem>
                  <SelectItem value="moderate">{t("suitability.moderate")}</SelectItem>
                  <SelectItem value="aggressive">{t("suitability.aggressive")}</SelectItem>
                </SelectContent>
              </Select>
            </Field>
          )}
          <Field
            label={t("common.notes")}
            htmlFor="client-notes"
            className="md:col-span-2"
            hint={t("common.optional")}
          >
            <Textarea
              id="client-notes"
              placeholder={t("clients.notesPlaceholder")}
              {...form.register("notes")}
            />
          </Field>

          {errors.root ? (
            <p
              role="alert"
              className="border border-negative px-3 py-2 text-sm text-negative md:col-span-2"
            >
              {errors.root.message}
            </p>
          ) : null}

          <DialogFooter className="md:col-span-2">
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="submit" loading={isPending}>
              {isPending ? t("common.saving") : submitLabel}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
