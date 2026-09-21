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

import { type Client, useAssessSuitability } from "@/entities/client/api"
import { toProblem } from "@/shared/api/problem"
import { useI18n } from "@/shared/i18n/provider"

const QUESTION_COUNT = 5

function profileFromScore(score: number): "conservative" | "moderate" | "aggressive" {
  if (score < 35) return "conservative"
  if (score < 70) return "moderate"
  return "aggressive"
}

function presetAnswers(profile: string): number[] {
  if (profile === "conservative") return [0, 1, 1, 0, 1]
  if (profile === "moderate") return [2, 2, 2, 2, 2]
  return [4, 4, 3, 4, 4]
}

/** Re-assesses an existing client's suitability profile. */
export function SuitabilityDialog({
  client,
  open,
  onOpenChange,
}: {
  client: Client
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { t } = useI18n()
  const assess = useAssessSuitability()
  const [answers, setAnswers] = useState<number[]>(() => presetAnswers(client.suitability))
  const [error, setError] = useState<string | null>(null)

  const total = answers.reduce((sum, answer) => sum + answer, 0)
  const score = Math.round((total / (QUESTION_COUNT * 4)) * 100)
  const profile = profileFromScore(score)

  const submit = async () => {
    try {
      await assess.mutateAsync({ id: client.id, answers })
      toast.success(t("clients.assessed"))
      onOpenChange(false)
    } catch (cause) {
      setError(toProblem(cause).detail)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent aria-describedby={undefined}>
        <DialogHeader>
          <DialogTitle>{t("clients.assessed")}</DialogTitle>
          <DialogDescription>
            {client.name} · {t("clients.answersHint")}
          </DialogDescription>
        </DialogHeader>

        <div className="form-grid two">
          {answers.map((answer, index) => (
            <Field
              // biome-ignore lint/suspicious/noArrayIndexKey: fixed-length questionnaire
              key={index}
              label={`${t("clients.answers")} ${index + 1}`}
              htmlFor={`answer-${index}`}
            >
              <Input
                id={`answer-${index}`}
                type="number"
                min={0}
                max={4}
                value={answer}
                onChange={(event) => {
                  const value = Math.max(0, Math.min(4, Number(event.target.value)))
                  setAnswers((current) =>
                    current.map((item, position) => (position === index ? value : item)),
                  )
                }}
              />
            </Field>
          ))}
        </div>

        <p className="mono mt-4 text-ash">
          {t("clients.score")}: {score} · {t(`suitability.${profile}` as "suitability.moderate")}
        </p>

        {error ? (
          <p role="alert" className="mt-3 border border-negative px-3 py-2 text-sm text-negative">
            {error}
          </p>
        ) : null}

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
            {t("common.cancel")}
          </Button>
          <Button type="button" loading={assess.isPending} onClick={() => void submit()}>
            {assess.isPending ? t("common.saving") : t("common.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
