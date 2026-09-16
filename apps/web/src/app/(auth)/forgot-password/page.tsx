import type { Metadata } from "next";

import { AuthHeading } from "@/features/auth/components/auth-heading";
import { ForgotPasswordForm } from "@/features/auth/components/forgot-password-form";

export const metadata: Metadata = { title: "Reset your password" };

export default function ForgotPasswordPage() {
  return (
    <>
      <AuthHeading
        title="Reset your password"
        description="Enter your email and we'll send you a link to choose a new one."
      />
      <ForgotPasswordForm />
    </>
  );
}
