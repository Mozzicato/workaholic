"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { routes } from "@/lib/routes";
import { createClient } from "@/lib/supabase/client";

import { authErrorMessage } from "../error-messages";
import { forgotPasswordSchema, type ForgotPasswordValues } from "../schemas";
import { CheckInboxAlert, FormErrorAlert } from "./form-alert";

export function ForgotPasswordForm() {
  const [formError, setFormError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  async function onSubmit({ email }: ForgotPasswordValues) {
    setFormError(null);
    const callback = new URL(routes.authCallback, window.location.origin);
    callback.searchParams.set("next", routes.resetPassword);
    const { error } = await createClient().auth.resetPasswordForEmail(email, {
      redirectTo: callback.toString(),
    });
    // Rate limits and outages are worth reporting; unknown addresses are not revealed.
    if (error && error.code !== "user_not_found") {
      setFormError(authErrorMessage(error));
      return;
    }
    setSentTo(email);
  }

  if (sentTo) {
    return (
      <div className="space-y-6">
        <CheckInboxAlert title="Check your inbox">
          If an account exists for <span className="font-medium text-foreground">{sentTo}</span>, a
          link to reset your password is on its way.
        </CheckInboxAlert>
        <BackToSignIn />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <FormErrorAlert message={formError} />
      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <FieldGroup>
          <Field data-invalid={Boolean(errors.email)}>
            <FieldLabel htmlFor="email">Email</FieldLabel>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              inputMode="email"
              className="h-10"
              aria-invalid={Boolean(errors.email)}
              {...register("email")}
            />
            <FieldError errors={[errors.email]} />
          </Field>
          <Button type="submit" size="lg" className="h-10 w-full" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null}
            {isSubmitting ? "Sending…" : "Send reset link"}
          </Button>
        </FieldGroup>
      </form>
      <BackToSignIn />
    </div>
  );
}

function BackToSignIn() {
  return (
    <p className="text-center text-sm text-muted-foreground">
      Remembered it?{" "}
      <Link href={routes.login} className="font-medium text-foreground underline-offset-4 hover:underline">
        Back to sign in
      </Link>
    </p>
  );
}
