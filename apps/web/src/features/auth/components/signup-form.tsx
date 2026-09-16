"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Spinner } from "@/components/ui/spinner";
import { routes } from "@/lib/routes";
import { createClient } from "@/lib/supabase/client";

import { authErrorMessage } from "../error-messages";
import { PASSWORD_MIN_LENGTH, signupSchema, type SignupValues } from "../schemas";
import { CheckInboxAlert, FormErrorAlert } from "./form-alert";
import { GoogleSignInButton } from "./google-sign-in-button";
import { OrDivider } from "./or-divider";

export function SignupForm({ googleEnabled }: { googleEnabled: boolean }) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: { fullName: "", email: "", password: "" },
  });

  async function onSubmit({ fullName, email, password }: SignupValues) {
    setFormError(null);
    const callback = new URL(routes.authCallback, window.location.origin);
    callback.searchParams.set("next", routes.dashboard);

    const { data, error } = await createClient().auth.signUp({
      email,
      password,
      options: { emailRedirectTo: callback.toString(), data: { full_name: fullName } },
    });
    if (error) {
      setFormError(authErrorMessage(error));
      return;
    }
    if (data.session) {
      // Email confirmation is disabled for this project: the user is already signed in.
      router.replace(routes.dashboard);
      router.refresh();
      return;
    }
    setSentTo(email);
  }

  if (sentTo) {
    return (
      <div className="space-y-6">
        <CheckInboxAlert title="Check your inbox">
          We sent a confirmation link to <span className="font-medium text-foreground">{sentTo}</span>.
          Open it on this device to finish creating your account.
        </CheckInboxAlert>
        <p className="text-center text-sm text-muted-foreground">
          Wrong address?{" "}
          <button
            type="button"
            onClick={() => setSentTo(null)}
            className="font-medium text-foreground underline-offset-4 hover:underline"
          >
            Start again
          </button>
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <FormErrorAlert message={formError} />

      {googleEnabled ? (
        <>
          <GoogleSignInButton next={routes.dashboard} onError={setFormError} />
          <OrDivider />
        </>
      ) : null}

      <form onSubmit={handleSubmit(onSubmit)} noValidate>
        <FieldGroup>
          <Field data-invalid={Boolean(errors.fullName)}>
            <FieldLabel htmlFor="fullName">Full name</FieldLabel>
            <Input
              id="fullName"
              autoComplete="name"
              className="h-10"
              aria-invalid={Boolean(errors.fullName)}
              {...register("fullName")}
            />
            <FieldError errors={[errors.fullName]} />
          </Field>

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

          <Field data-invalid={Boolean(errors.password)}>
            <FieldLabel htmlFor="password">Password</FieldLabel>
            <PasswordInput
              id="password"
              autoComplete="new-password"
              className="h-10"
              aria-invalid={Boolean(errors.password)}
              aria-describedby="password-hint"
              {...register("password")}
            />
            {errors.password ? (
              <FieldError errors={[errors.password]} />
            ) : (
              <FieldDescription id="password-hint">
                At least {PASSWORD_MIN_LENGTH} characters.
              </FieldDescription>
            )}
          </Field>

          <Button type="submit" size="lg" className="h-10 w-full" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null}
            {isSubmitting ? "Creating your account…" : "Create account"}
          </Button>
        </FieldGroup>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link href={routes.login} className="font-medium text-foreground underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
