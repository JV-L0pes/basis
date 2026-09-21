import type { components } from "@basis/contracts"

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
  toast,
} from "@basis/ui"
import { useState } from "react"

import { useSetTargets } from "@/entities/portfolio/api"
import { toProblem } from "@/shared/api/problem"
import { useI18n } from "@/shared/i18n/provider"

type Target = components["schemas"]["TargetWeightRequest"]

const CLASSES = ["equity", "fixed_income", "etf", "real_estate", "crypto", "cash"] as const

type Draft = Record<string, string>

function initialDraft(targets: components["schemas"]["TargetWeightResponse"][]): Draft {
  const draft: Draft = {}
  for (const target of targets) {
    draft[target.asset_class] = String(target.weight_percent)
  }
  return draft
}

export function TargetAllocationDialog({
  portfolioId,
  targets,
  open,
  onOpenChange,
}: {
  portfolioId: string
  targets: components["schemas"]["TargetWeightResponse"][]
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { t } = useI18n()
  const setTargets = useSetTargets(portfolioId)
  const [draft, setDraft] = useState<Draft>(() => initialDraft(targets))
  const [error, setError] = useState<string | null>(null)

  const total = CLASSES.reduce((sum, item) => sum + (Number(draft[item]) || 0), 0)

  const submit = async () => {
    if (Math.abs(total - 100) > 0.001) {
      setError(t("portfolios.targets"))
      return
    }
    const payload: Target[] = CLASSES.filter((item) => Number(draft[item]) > 0).map((item) => ({
      asset_class: item,
      weight_bps: Math.round((Number(draft[item]) || 0) * 100),
    }))
    try {
      await setTargets.mutateAsync(payload)
      toast.success(t("portfolios.targetsSaved"))
      onOpenChange(false)
    } catch (cause) {
      setError(toProblem(cause).detail)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby={undefined}>
        <DialogHeader>
          <DialogTitle>{t("portfolios.setTargets")}</DialogTitle>
          <DialogDescription>{t("portfolios.noTargets")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          {CLASSES.map((assetClass) => (
            <Field
              key={assetClass}
              label={t(`assetClass.${assetClass}` as "assetClass.equity")}
              htmlFor={`target-${assetClass}`}
            >
              <Input
                id={`target-${assetClass}`}
                type="number"
                min={0}
                max={100}
                step={1}
                value={draft[assetClass] ?? ""}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, [assetClass]: event.target.value }))
                }
              />
            </Field>
          ))}

          <p className="mono text-ash">
            {t("common.total")}: {total.toFixed(0)}%
          </p>

          {error ? (
            <p role="alert" className="border border-negative px-3 py-2 text-sm text-negative">
              {error}
            </p>
          ) : null}

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              {t("common.cancel")}
            </Button>
            <Button type="button" loading={setTargets.isPending} onClick={() => void submit()}>
              {setTargets.isPending ? t("common.saving") : t("common.save")}
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  )
}
