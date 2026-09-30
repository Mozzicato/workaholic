import { Logo } from "@/components/brand/logo";
import { routes } from "@/lib/routes";

import { MainNav } from "./main-nav";
import { UserMenu } from "./user-menu";
import { Walkthrough } from "./walkthrough";

export function AppHeader({ email }: { email: string | null }) {
  return (
    <header className="sticky top-0 z-30 border-b border-border/70 bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/70">
      <div className="mx-auto flex h-14 w-full max-w-5xl items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex min-w-0 items-center gap-4 sm:gap-6">
          <Logo href={routes.dashboard} />
          <MainNav />
        </div>
        <div className="flex items-center gap-1 sm:gap-2">
          <Walkthrough />
          <UserMenu email={email} />
        </div>
      </div>
    </header>
  );
}
