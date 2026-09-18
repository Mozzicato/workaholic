import Link from "next/link";

import { Logo } from "@/components/brand/logo";
import { routes } from "@/lib/routes";

/** Public: the guides are useful before anyone signs up, and must never block the workflow. */
export default function LearnLayout({ children }: LayoutProps<"/learn">) {
  return (
    <div className="flex min-h-dvh flex-col">
      <header className="border-b border-border/70">
        <div className="mx-auto flex h-14 w-full max-w-3xl items-center justify-between gap-4 px-4 sm:px-6">
          <Logo href={routes.home} />
          <Link
            href={routes.dashboard}
            className="text-sm text-muted-foreground transition-colors hover:text-foreground"
          >
            Your resumes
          </Link>
        </div>
      </header>
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-8 sm:px-6 sm:py-12">{children}</main>
    </div>
  );
}
