"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Spinner } from "@/components/ui/spinner";
import { routes } from "@/lib/routes";
import { createClient } from "@/lib/supabase/client";

import { authErrorMessage } from "../error-messages";
import { loginSchema, type LoginValues } from "../schemas";
import { FormErrorAlert } from "./form-alert";
import { GoogleSignInButton } from "./google-sign-in-button";
import { OrDivider } from "./or-divider";

type LoginFormProps = {
  next: string;
  initialError?: string | null;
  googleEnabled: boolean;
};

export function LoginForm({ next, initialError = null, googleEnabled }: LoginFormProps) {
  const router = useRouter();
  const [formError, setFormError] = useState<string | null>(initialError);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
  });

  async function onSubmit(values: LoginValues) {
    setFormError(null);
    const { error } = await createClient().auth.signInWithPassword(values);
    if (error) {
      setFormError(authErrorMessage(error));
      return;
    }
    router.replace(next);
    router.refresh();
  }

  return (
    <div className="space-y-6">
      <FormErrorAlert message={formError} />

      {googleEnabled ? (
        <>
          <GoogleSignInButton next={next} onError={setFormError} />
          <OrDivider />
        </>
      ) : null}

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

          <Field data-invalid={Boolean(errors.password)}>
            <div className="flex items-center justify-between">
              <FieldLabel htmlFor="password">Password</FieldLabel>
              <Link
                href={routes.forgotPassword}
                className="text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
              >
                Forgot password?
              </Link>
            </div>
            <PasswordInput
              id="password"
              autoComplete="current-password"
              className="h-10"
              aria-invalid={Boolean(errors.password)}
              {...register("password")}
            />
            <FieldError errors={[errors.password]} />
          </Field>

          <Button type="submit" size="lg" className="h-10 w-full" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null}
            {isSubmitting ? "Signing in…" : "Sign in"}
          </Button>
        </FieldGroup>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        New to Workaholic?{" "}
        <Link href={routes.signup} className="font-medium text-foreground underline-offset-4 hover:underline">
          Create an account
        </Link>
      </p>
    </div>
  );
}
