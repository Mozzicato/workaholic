"use client";

import { FileTextIcon, RotateCwIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { CurrentUser } from "@/features/account/api";
import { useCurrentUser } from "@/features/account/hooks";
import { ApiError, errorMessage } from "@/lib/api/errors";

const PROVIDER_LABELS: Record<string, string> = {
  email: "Email and password",
  google: "Google",
};

export function DashboardView() {
  const { data: user, error, isPending, refetch, isRefetching } = useCurrentUser();

  if (isPending) return <DashboardSkeleton />;

  if (error) {
    return (
      <div role="alert" className="mx-auto max-w-md rounded-xl border bg-card p-8 text-center">
        <h1 className="font-heading text-3xl">We couldn&apos;t load your dashboard</h1>
        <p className="mt-2 text-sm text-muted-foreground">{errorMessage(error)}</p>
        <Button className="mt-6" variant="outline" onClick={() => refetch()} disabled={isRefetching}>
          <RotateCwIcon className={isRefetching ? "animate-spin" : undefined} aria-hidden="true" />
          Try again
        </Button>
        {error instanceof ApiError && error.requestId ? (
          <p className="mt-4 font-mono text-[11px] text-muted-foreground">Reference: {error.requestId}</p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="space-y-10">
      <header className="space-y-1">
        <p className="text-sm text-muted-foreground">{greetingForNow()}</p>
        <h1 className="font-heading text-4xl tracking-tight sm:text-5xl">
          {user.name ? `Hi, ${firstName(user.name)}` : "Welcome to Workaholic"}
        </h1>
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <ResumesSection />
        <AccountSection user={user} />
      </div>
    </div>
  );
}

function ResumesSection() {
  return (
    <section aria-labelledby="resumes-heading" className="space-y-4">
      <h2 id="resumes-heading" className="text-sm font-medium text-muted-foreground">
        Your resumes
      </h2>
      <div className="relative overflow-hidden rounded-xl border border-dashed border-border bg-card px-6 py-12 text-center sm:px-10">
        <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-accent text-accent-foreground">
          <FileTextIcon className="size-5" aria-hidden="true" />
        </div>
        <p className="mt-5 font-heading text-2xl">You haven&apos;t created a resume yet.</p>
        <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
          Resume creation is the next part of Workaholic being built. When it arrives, you&apos;ll
          start here by talking through what you&apos;ve actually done.
        </p>
        <Button className="mt-6" size="lg" disabled>
          Create resume — coming next
        </Button>
      </div>
    </section>
  );
}

function AccountSection({ user }: { user: CurrentUser }) {
  return (
    <section aria-labelledby="account-heading" className="space-y-4">
      <h2 id="account-heading" className="text-sm font-medium text-muted-foreground">
        Account
      </h2>
      <dl className="divide-y rounded-xl border bg-card text-sm">
        <AccountRow label="Email" value={user.email ?? "—"} />
        <AccountRow label="Sign-in method" value={PROVIDER_LABELS[user.auth_provider] ?? user.auth_provider} />
        <AccountRow
          label="Member since"
          value={new Intl.DateTimeFormat(undefined, { dateStyle: "long" }).format(new Date(user.created_at))}
        />
      </dl>
    </section>
  );
}

function AccountRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="space-y-0.5 px-4 py-3">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="truncate font-medium">{value}</dd>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-10" aria-busy="true" aria-label="Loading your dashboard">
      <div className="space-y-3">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-12 w-64" />
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <Skeleton className="h-72 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
    </div>
  );
}

function firstName(name: string): string {
  return name.trim().split(/\s+/)[0];
}

function greetingForNow(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}
