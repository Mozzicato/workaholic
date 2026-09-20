import { redirect } from "next/navigation";

import { AppProviders } from "@/components/providers/app-providers";
import { AppHeader } from "@/features/account/components/app-header";
import { FeedbackButton } from "@/features/support/components/feedback-button";
import { routes } from "@/lib/routes";
import { getVerifiedClaims } from "@/lib/supabase/server";

export default async function AppLayout({ children }: LayoutProps<"/">) {
  // Verified here as well as in the proxy: a matcher change must never expose these pages.
  const claims = await getVerifiedClaims();
  if (!claims) redirect(routes.login);

  return (
    <AppProviders>
      <div className="flex min-h-dvh flex-col">
        <AppHeader email={typeof claims.email === "string" ? claims.email : null} />
        <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6 sm:py-12">
          {children}
        </main>
        <FeedbackButton />
      </div>
    </AppProviders>
  );
}
