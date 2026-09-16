import type { Metadata } from "next";
import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { AuthHeading } from "@/features/auth/components/auth-heading";
import { ResetPasswordForm } from "@/features/auth/components/reset-password-form";
import { routes } from "@/lib/routes";
import { getVerifiedClaims } from "@/lib/supabase/server";

export const metadata: Metadata = { title: "Choose a new password" };

export default async function ResetPasswordPage() {
  // The recovery link signs the user in; without that session the link was invalid or used.
  const claims = await getVerifiedClaims();

  if (!claims) {
    return (
      <>
        <AuthHeading
          title="This link has expired"
          description="Password reset links work once and expire after a short time. Request a new one."
        />
        <Link href={routes.forgotPassword} className={buttonVariants({ size: "lg", className: "h-10 w-full" })}>
          Send a new link
        </Link>
      </>
    );
  }

  return (
    <>
      <AuthHeading title="Choose a new password" description="You'll use it the next time you sign in." />
      <ResetPasswordForm />
    </>
  );
}
