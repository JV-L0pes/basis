import { Button, Field, Input, toast } from "@basis/ui"
import { zodResolver } from "@hookform/resolvers/zod"
import { useNavigate } from "@tanstack/react-router"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { register } from "@/entities/session/api"
import { useSessionStore } from "@/entities/session/store"
import { toProblem } from "@/shared/api/problem"
import { useI18n } from "@/shared/i18n/provider"

const schema = z.object({
  display_name: z.string().min(2, "common.required"),
  email: z.email("common.required"),
  password: z
    .string()
    .min(10, "auth.registerPasswordHint")
    .regex(/[A-Za-z]/, "auth.registerPasswordHint")
    .regex(/\d/, "auth.registerPasswordHint"),
})

type FormValues = z.infer<typeof schema>

export function RegisterForm() {
  const { t } = useI18n()
  const navigate = useNavigate()
  const setSession = useSessionStore((state) => state.setSession)

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { display_name: "", email: "", password: "" },
  })

  const onSubmit = form.handleSubmit(async (values) => {
    try {
      const result = await register(values)
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
        message:
          problem.code === "conflict" ? t("auth.registerEmailTaken") : t("auth.registerError"),
      })
    }
  })

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5">
      <Field
        label={t("auth.name")}
        htmlFor="display-name"
        required
        error={form.formState.errors.display_name ? t("common.required") : undefined}
      >
        <Input
          id="display-name"
          autoComplete="name"
          aria-invalid={Boolean(form.formState.errors.display_name)}
          {...form.register("display_name")}
        />
      </Field>

      <Field
        label={t("auth.email")}
        htmlFor="register-email"
        required
        error={form.formState.errors.email ? t("common.required") : undefined}
      >
        <Input
          id="register-email"
          type="email"
          autoComplete="email"
          aria-invalid={Boolean(form.formState.errors.email)}
          {...form.register("email")}
        />
      </Field>

      <Field
        label={t("auth.password")}
        htmlFor="register-password"
        required
        hint={t("auth.registerPasswordHint")}
        error={form.formState.errors.password ? t("auth.registerPasswordHint") : undefined}
      >
        <Input
          id="register-password"
          type="password"
          autoComplete="new-password"
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
        {form.formState.isSubmitting ? t("auth.registerSubmitting") : t("auth.registerSubmit")}
      </Button>
    </form>
  )
}
