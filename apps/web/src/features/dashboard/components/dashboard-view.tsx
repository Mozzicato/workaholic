"use client";

import Link from "next/link";

import { LoadFailure } from "@/components/feedback/load-failure";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { CurrentUser } from "@/features/account/api";
import { useCurrentUser } from "@/features/account/hooks";
import { useProfile } from "@/features/profile/hooks";
import { CreateResumeDialog } from "@/features/resumes/components/create-resume-dialog";
import { ResumeList } from "@/features/resumes/components/resume-list";
import { useResumes } from "@/features/resumes/hooks";
import { cn } from "@/lib/utils";

const PROVIDER_LABELS: Record<string, string> = {
  email: "Email and password",
  google: "Google",
};

export function DashboardView() {
  const account = useCurrentUser();
  const resumes = useResumes();
  const profile = useProfile();

  // Checked one query at a time: that is what narrows each result to its loaded shape.
  if (account.isPending) return <DashboardSkeleton />;
  if (resumes.isPending) return <DashboardSkeleton />;

  const retry = () => {
    void account.refetch();
    void resumes.refetch();
  };
  const retrying = account.isRefetching || resumes.isRefetching;

  if (account.isError) {
    return (
      <LoadFailure
        error={account.error}
        onRetry={retry}
        retrying={retrying}
        title="We couldn't load your dashboard"
      />
    );
  }
  if (resumes.isError) {
    return (
      <LoadFailure
        error={resumes.error}
        onRetry={retry}
        retrying={retrying}
        title="We couldn't load your resumes"
      />
    );
  }

  const user = account.data;
  const profileItems = profile.data
    ? profile.data.experience.length + profile.data.projects.length + profile.data.skills.length
    : 0;

  return (
    <div className="space-y-10">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <p className="text-sm text-muted-foreground">{greetingForNow()}</p>
          <h1 className="font-heading text-4xl tracking-tight sm:text-5xl">
            {user.name ? `Hi, ${firstName(user.name)}` : "Welcome to Workaholic"}
          </h1>
        </div>
        {resumes.data.length > 0 ? <CreateResumeDialog /> : null}
      </header>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <section aria-labelledby="resumes-heading" className="space-y-4">
          <h2 id="resumes-heading" className="text-sm font-medium text-muted-foreground">
            Your resumes
          </h2>
          <ResumeList resumes={resumes.data} />
        </section>

        <div className="space-y-6">
          <section aria-labelledby="profile-heading" className="space-y-4">
            <h2 id="profile-heading" className="text-sm font-medium text-muted-foreground">
              Your career record
            </h2>
            <div className="rounded-xl border bg-card p-5">
              <p className="text-sm leading-relaxed text-muted-foreground">
                {profileItems > 0
                  ? `${profileItems} item${profileItems === 1 ? "" : "s"} recorded so far. Resumes are written from this.`
                  : "Empty so far. Add what you've done, and resumes get written from it."}
              </p>
              <Link
                href="/profile"
                className={cn(buttonVariants({ variant: "outline" }), "mt-4 h-9 w-full")}
              >
                {profileItems > 0 ? "Review your record" : "Add your experience"}
              </Link>
            </div>
          </section>

          <AccountSection user={user} />
        </div>
      </div>
    </div>
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
        <AccountRow
          label="Sign-in method"
          value={PROVIDER_LABELS[user.auth_provider] ?? user.auth_provider}
        />
        <AccountRow
          label="Member since"
          value={new Intl.DateTimeFormat(undefined, {
            dateStyle: "long",
          }).format(new Date(user.created_at))}
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
