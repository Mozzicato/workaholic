import type { Metadata } from "next";

import { AuthHeading } from "@/features/auth/components/auth-heading";
import { SignupForm } from "@/features/auth/components/signup-form";
import { env } from "@/lib/env";

export const metadata: Metadata = { title: "Create your account" };

export default function SignupPage() {
  return (
    <>
      <AuthHeading
        title="Start with what's true"
        description="Create an account, then tell Workaholic what you've actually done."
      />
      <SignupForm googleEnabled={env.NEXT_PUBLIC_AUTH_GOOGLE_ENABLED} />
    </>
  );
}
