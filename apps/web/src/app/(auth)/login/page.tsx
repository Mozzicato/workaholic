import type { Metadata } from "next";

import { AuthHeading } from "@/features/auth/components/auth-heading";
import { LoginForm } from "@/features/auth/components/login-form";
import { CALLBACK_ERROR_MESSAGES } from "@/features/auth/error-messages";
import { env } from "@/lib/env";
import { safeNextPath } from "@/lib/routes";

export const metadata: Metadata = { title: "Sign in" };

export default async function LoginPage({ searchParams }: PageProps<"/login">) {
  const params = await searchParams;
  const next = safeNextPath(typeof params.next === "string" ? params.next : null);
  const errorKey = typeof params.error === "string" ? params.error : null;
  const initialError = errorKey ? (CALLBACK_ERROR_MESSAGES[errorKey] ?? null) : null;

  return (
    <>
      <AuthHeading title="Welcome back" description="Sign in to pick up where you left off." />
      <LoginForm
        next={next}
        initialError={initialError}
        googleEnabled={env.NEXT_PUBLIC_AUTH_GOOGLE_ENABLED}
      />
    </>
  );
}
