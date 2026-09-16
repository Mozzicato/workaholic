"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { PasswordInput } from "@/components/ui/password-input";
import { Spinner } from "@/components/ui/spinner";
import { routes } from "@/lib/routes";
import { createClient } from "@/lib/supabase/client";

import { authErrorMessage } from "../error-messages";
import { PASSWORD_MIN_LENGTH, resetPasswordSchema, type ResetPasswordValues } from "../schemas";
import { FormErrorAlert } from "./form-alert";

export function ResetPasswordForm() {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { password: "", confirmPassword: "" },
  });

  async function onSubmit({ password }: ResetPasswordValues) {
    setFormError(null);
    const { error } = await createClient().auth.updateUser({ password });
    if (error) {
      setFormError(authErrorMessage(error));
      return;
    }
    toast.success("Password updated");
    router.replace(routes.dashboard);
    router.refresh();
  }

  return (
    <div className="space-y-6">
      <FormErrorAlert message={formError} />
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <FieldGroup>
          <Field data-invalid={Boolean(errors.password)}>
            <FieldLabel htmlFor="password">New password</FieldLabel>
            <PasswordInput
              id="password"
              autoComplete="new-password"
              className="h-10"
              aria-invalid={Boolean(errors.password)}
              {...register("password")}
            />
            {errors.password ? (
              <FieldError errors={[errors.password]} />
            ) : (
              <FieldDescription>At least {PASSWORD_MIN_LENGTH} characters.</FieldDescription>
            )}
          </Field>
          <Field data-invalid={Boolean(errors.confirmPassword)}>
            <FieldLabel htmlFor="confirmPassword">Confirm new password</FieldLabel>
            <PasswordInput
              id="confirmPassword"
              autoComplete="new-password"
              className="h-10"
              aria-invalid={Boolean(errors.confirmPassword)}
              {...register("confirmPassword")}
            />
            <FieldError errors={[errors.confirmPassword]} />
          </Field>
          <Button type="submit" size="lg" className="h-10 w-full" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null}
            {isSubmitting ? "Saving…" : "Save new password"}
          </Button>
        </FieldGroup>
      </form>
    </div>
  );
}
