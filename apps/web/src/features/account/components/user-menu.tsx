"use client";

import { useQueryClient } from "@tanstack/react-query";
import { LogOutIcon, MonitorIcon, MoonIcon, SunIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useState } from "react";
import { toast } from "sonner";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { routes } from "@/lib/routes";
import { createClient } from "@/lib/supabase/client";

import { useCurrentUser } from "../hooks";

function initialsFor(name: string | null, email: string | null): string {
  const source = name?.trim() || email?.split("@")[0] || "";
  const parts = source.split(/[\s._-]+/).filter(Boolean);
  const initials = parts.length > 1 ? `${parts[0][0]}${parts[parts.length - 1][0]}` : source.slice(0, 2);
  return initials.toUpperCase() || "?";
}

export function UserMenu({ email }: { email: string | null }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { theme = "system", setTheme } = useTheme();
  const { data: user } = useCurrentUser();
  const [signingOut, setSigningOut] = useState(false);

  const displayEmail = user?.email ?? email;
  const initials = initialsFor(user?.name ?? null, displayEmail);

  async function signOut() {
    setSigningOut(true);
    const { error } = await createClient().auth.signOut();
    if (error) {
      setSigningOut(false);
      toast.error("We couldn't sign you out. Please try again.");
      return;
    }
    queryClient.clear(); // never leave one account's data in memory for the next
    router.replace(routes.login);
    router.refresh();
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Account menu"
        className="flex size-9 items-center justify-center rounded-full bg-secondary text-xs font-semibold tracking-wide text-secondary-foreground ring-1 ring-border outline-none transition-colors hover:bg-muted focus-visible:ring-3 focus-visible:ring-ring/50 data-[popup-open]:bg-muted"
      >
        {initials}
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <DropdownMenuGroup>
          <DropdownMenuLabel className="flex flex-col gap-0.5 py-2">
            <span className="truncate text-sm font-medium text-foreground">
              {user?.name ?? "Signed in"}
            </span>
            {displayEmail ? (
              <span className="truncate text-xs font-normal text-muted-foreground">{displayEmail}</span>
            ) : null}
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuLabel className="text-xs text-muted-foreground">Appearance</DropdownMenuLabel>
          <DropdownMenuRadioGroup value={theme} onValueChange={(value) => setTheme(String(value))}>
            <DropdownMenuRadioItem value="light">
              <SunIcon aria-hidden="true" /> Light
            </DropdownMenuRadioItem>
            <DropdownMenuRadioItem value="dark">
              <MoonIcon aria-hidden="true" /> Dark
            </DropdownMenuRadioItem>
            <DropdownMenuRadioItem value="system">
              <MonitorIcon aria-hidden="true" /> System
            </DropdownMenuRadioItem>
          </DropdownMenuRadioGroup>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={signOut} disabled={signingOut}>
          <LogOutIcon aria-hidden="true" />
          {signingOut ? "Signing out…" : "Sign out"}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
