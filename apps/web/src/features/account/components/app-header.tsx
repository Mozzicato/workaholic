import { Logo } from "@/components/brand/logo";
import { routes } from "@/lib/routes";

import { UserMenu } from "./user-menu";

export function AppHeader({ email }: { email: string | null }) {
  return (
    <header className="sticky top-0 z-30 border-b border-border/70 bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-14 w-full max-w-5xl items-center justify-between gap-4 px-4 sm:px-6">
        <Logo href={routes.dashboard} />
        <UserMenu email={email} />
      </div>
    </header>
  );
}
