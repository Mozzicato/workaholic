"use client";

import { CheckIcon, DownloadIcon, RefreshCwIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { LoadFailure } from "@/components/feedback/load-failure";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { useCurrentUser } from "@/features/account/hooks";
import {
  downloadTemplateRequest,
  type AdminStats,
  type Feedback,
  type TemplateRequest,
} from "@/features/support/api";
import {
  useAdminFeedback,
  useAdminStats,
  useAdminTemplateRequests,
  useAdminUsers,
  useMarkFeedback,
  useMarkTemplateRequest,
} from "@/features/support/hooks";
import { getApiClient } from "@/lib/api/browser";
import { errorMessage } from "@/lib/api/errors";
import { templateInfo } from "@/features/resumes/templates";
import { cn } from "@/lib/utils";

/**
 * How Workaholic is being used, for whoever runs it.
 *
 * Counts, and the messages people chose to send. No resume, profile, interview answer or job
 * advert appears here: running the service does not require reading what people wrote.
 */
export function AdminView() {
  const account = useCurrentUser();
  const stats = useAdminStats();

  if (account.isPending) return <Skeleton className="h-64 rounded-xl" />;
  if (account.data && !account.data.is_admin) {
    return (
      <div className="rounded-xl border border-dashed p-8 text-center">
        <h1 className="font-heading text-2xl">Administrators only</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          This page is for the people who run Workaholic.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="font-heading text-4xl tracking-tight sm:text-5xl">Dashboard</h1>
          <p className="text-muted-foreground">
            {stats.data
              ? `As of ${new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(stats.data.generated_at))}`
              : "Counts only — never anyone's resume."}
          </p>
        </div>
        <Button variant="outline" onClick={() => void stats.refetch()} disabled={stats.isFetching}>
          {stats.isFetching ? <Spinner /> : <RefreshCwIcon aria-hidden="true" />}
          Refresh
        </Button>
      </header>

      {stats.isError ? (
        <LoadFailure
          error={stats.error}
          onRetry={() => void stats.refetch()}
          retrying={stats.isRefetching}
          title="We couldn't load the numbers"
        />
      ) : stats.data ? (
        <Numbers stats={stats.data} />
      ) : (
        <Skeleton className="h-40 rounded-xl" />
      )}

      <FeedbackList />
      <TemplateRequests />
      <Accounts />
    </div>
  );
}

function Numbers({ stats }: { stats: AdminStats }) {
  const cards: { label: string; value: number; note?: string }[] = [
    { label: "Accounts", value: stats.users_total, note: `${stats.users_last_7_days} this week` },
    {
      label: "Records ready for a resume",
      value: stats.records_ready_for_a_resume,
      note: `of ${stats.users_total} accounts`,
    },
    { label: "Resumes", value: stats.resumes_total, note: `${stats.letters_total} cover letters` },
    { label: "Drafts written", value: stats.drafts_total, note: `${stats.drafts_last_7_days} this week` },
    {
      label: "Assistant conversations",
      value: stats.interviews_started,
      note: `${stats.interviews_completed} finished`,
    },
    { label: "CVs imported", value: stats.documents_imported },
    { label: "Jobs saved", value: stats.jobs_saved },
    {
      label: "Active this week",
      value: Math.max(stats.wrote_a_draft_last_7_days, stats.used_the_assistant_last_7_days),
      note: `${stats.wrote_a_draft_last_7_days} wrote · ${stats.used_the_assistant_last_7_days} talked`,
    },
  ];

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => (
          <div key={card.label} className="rounded-xl border bg-card p-4">
            <p className="text-sm text-muted-foreground">{card.label}</p>
            <p className="font-heading text-3xl">{card.value}</p>
            {card.note ? <p className="text-xs text-muted-foreground">{card.note}</p> : null}
          </div>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Bars
          title="Templates in use"
          rows={stats.templates_in_use.map((row) => ({
            label: templateInfo(row.label as never).name ?? row.label,
            count: row.count,
          }))}
          empty="No resumes yet."
        />
        <Bars
          title="Sign-ups, last 30 days"
          rows={stats.signups_by_day}
          empty="No sign-ups in the last 30 days."
        />
      </div>
    </div>
  );
}

function Bars({
  title,
  rows,
  empty,
}: {
  title: string;
  rows: { label: string; count: number }[];
  empty: string;
}) {
  const highest = Math.max(1, ...rows.map((row) => row.count));
  return (
    <section className="rounded-xl border bg-card p-5">
      <h2 className="font-heading text-lg">{title}</h2>
      {rows.length === 0 ? (
        <p className="mt-3 text-sm text-muted-foreground">{empty}</p>
      ) : (
        <ul className="mt-3 space-y-2">
          {rows.map((row) => (
            <li key={row.label} className="grid grid-cols-[8rem_1fr_2rem] items-center gap-2">
              <span className="truncate text-sm">{row.label}</span>
              <span className="h-2 rounded-full bg-muted">
                <span
                  className="block h-2 rounded-full bg-primary"
                  style={{ width: `${(row.count / highest) * 100}%` }}
                />
              </span>
              <span className="text-right text-sm tabular-nums">{row.count}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function FeedbackList() {
  const feedback = useAdminFeedback();
  const mark = useMarkFeedback();
  const entries = feedback.data ?? [];

  return (
    <section className="space-y-3">
      <h2 className="font-heading text-xl">
        Feedback {entries.length > 0 ? `(${entries.filter((e) => e.status === "new").length} new)` : ""}
      </h2>
      {feedback.isPending ? <Skeleton className="h-24 rounded-xl" /> : null}
      {entries.length === 0 && !feedback.isPending ? (
        <p className="rounded-xl border border-dashed p-5 text-sm text-muted-foreground">
          Nothing yet.
        </p>
      ) : null}
      <ul className="space-y-2">
        {entries.map((entry: Feedback) => (
          <li
            key={entry.id}
            className={cn(
              "rounded-xl border bg-card p-4",
              entry.status === "done" && "opacity-60",
            )}
          >
            <p className="text-sm whitespace-pre-wrap">{entry.message}</p>
            <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
              <span>
                {entry.email ?? "no address"} · {entry.page ?? "unknown page"} ·{" "}
                {new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
                  new Date(entry.created_at),
                )}
              </span>
              <Button
                variant="ghost"
                size="sm"
                disabled={mark.isPending}
                onClick={() =>
                  mark.mutate(
                    { id: entry.id, status: entry.status === "new" ? "done" : "new" },
                    { onError: (error) => toast.error(errorMessage(error)) },
                  )
                }
              >
                <CheckIcon aria-hidden="true" />
                {entry.status === "new" ? "Mark done" : "Reopen"}
              </Button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function TemplateRequests() {
  const requests = useAdminTemplateRequests();
  const mark = useMarkTemplateRequest();
  const [downloading, setDownloading] = useState<string | null>(null);
  const entries = requests.data ?? [];

  async function onDownload(request: TemplateRequest) {
    setDownloading(request.id);
    try {
      await downloadTemplateRequest(getApiClient(), request);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setDownloading(null);
    }
  }

  return (
    <section className="space-y-3">
      <h2 className="font-heading text-xl">Templates people sent in</h2>
      {entries.length === 0 ? (
        <p className="rounded-xl border border-dashed p-5 text-sm text-muted-foreground">
          Nothing yet.
        </p>
      ) : (
        <ul className="space-y-2">
          {entries.map((request) => (
            <li
              key={request.id}
              className={cn(
                "flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card p-4",
                request.status === "done" && "opacity-60",
              )}
            >
              <div className="min-w-0">
                <p className="truncate font-medium">{request.filename}</p>
                <p className="text-xs text-muted-foreground">
                  {request.email ?? "no address"} · {Math.round(request.size_bytes / 1024)} KB ·{" "}
                  {new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
                    new Date(request.created_at),
                  )}
                </p>
                {request.note ? <p className="mt-1 text-sm">{request.note}</p> : null}
              </div>
              <div className="flex gap-1">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={downloading === request.id}
                  onClick={() => void onDownload(request)}
                >
                  {downloading === request.id ? <Spinner /> : <DownloadIcon aria-hidden="true" />}
                  Download
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={mark.isPending}
                  onClick={() =>
                    mark.mutate(
                      { id: request.id, status: request.status === "new" ? "done" : "new" },
                      { onError: (error) => toast.error(errorMessage(error)) },
                    )
                  }
                >
                  <CheckIcon aria-hidden="true" />
                  {request.status === "new" ? "Mark done" : "Reopen"}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Accounts() {
  const users = useAdminUsers();
  const entries = users.data ?? [];

  return (
    <section className="space-y-3">
      <h2 className="font-heading text-xl">Accounts</h2>
      {users.isPending ? <Skeleton className="h-32 rounded-xl" /> : null}
      {entries.length > 0 ? (
        <div className="overflow-x-auto rounded-xl border bg-card">
          <table className="w-full text-sm">
            <thead className="border-b text-left text-xs text-muted-foreground">
              <tr>
                <th className="px-4 py-2 font-medium">Email</th>
                <th className="px-4 py-2 font-medium">Joined</th>
                <th className="px-4 py-2 font-medium">Record</th>
                <th className="px-4 py-2 text-right font-medium">Resumes</th>
                <th className="px-4 py-2 text-right font-medium">Drafts</th>
                <th className="px-4 py-2 text-right font-medium">Chats</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {entries.map((user) => (
                <tr key={user.id}>
                  <td className="px-4 py-2">{user.email ?? "—"}</td>
                  <td className="px-4 py-2 text-muted-foreground">
                    {new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
                      new Date(user.created_at),
                    )}
                  </td>
                  <td className="px-4 py-2">
                    {user.record_ready ? "Ready" : <span className="text-muted-foreground">—</span>}
                  </td>
                  <td className="px-4 py-2 text-right tabular-nums">{user.resumes}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{user.drafts}</td>
                  <td className="px-4 py-2 text-right tabular-nums">{user.interviews}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
