import { Button, Field, Input, toast } from "@basis/ui"
import { zodResolver } from "@hookform/resolvers/zod"
import { useNavigate } from "@tanstack/react-router"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { login } from "@/entities/session/api"
import { useSessionStore } from "@/entities/session/store"
import { toProblem } from "@/shared/api/problem"
import { useI18n } from "@/shared/i18n/provider"

const schema = z.object({
  email: z.string().min(3, "common.required").email("clients.email"),
  password: z.string().min(1, "common.required"),
})

type FormValues = z.infer<typeof schema>

export function LoginForm() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const setSession = useSessionStore((state) => state.setSession)

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "" },
  })

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      const result = await login(values.email, values.password)
      setSession({
        user: result.user,
        accessToken: result.token.access_token,
        expiresIn: result.token.expires_in,
      })
      toast.success(t("auth.welcome", { name: result.user.display_name }))
      await navigate({ to: "/" })
    } catch (error) {
      const problem = toProblem(error)
      form.setError("root", {
        message: problem.code === "unauthenticated" ? t("auth.error") : problem.detail,
      })
    }
  })

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
      <Field
        label={t("auth.email")}
        htmlFor="email"
        required
        error={form.formState.errors.email ? t("common.required") : undefined}
      >
        <Input
          id="email"
          type="email"
          autoComplete="email"
          aria-invalid={Boolean(form.formState.errors.email)}
          {...form.register("email")}
        />
      </Field>

      <Field
        label={t("auth.password")}
        htmlFor="password"
        required
        error={form.formState.errors.password ? t("common.required") : undefined}
      >
        <Input
          id="password"
          type="password"
          autoComplete="current-password"
          aria-invalid={Boolean(form.formState.errors.password)}
          {...form.register("password")}
        />
      </Field>

      {form.formState.errors.root ? (
        <p role="alert" className="border border-negative px-3 py-2 text-sm text-negative">
          {form.formState.errors.root.message}
        </p>
      ) : null}

      <Button type="submit" loading={form.formState.isSubmitting} size="lg">
        {form.formState.isSubmitting ? t("auth.submitting") : t("auth.submit")}
      </Button>
    </form>
  )
}
