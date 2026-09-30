"use client";

import { DownloadIcon, SearchIcon } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { LoadFailure } from "@/components/feedback/load-failure";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import type { HistoryEntry } from "@/features/resumes/api";
import { useDownloadPdf, useHistory } from "@/features/resumes/hooks";
import { templateInfo } from "@/features/resumes/templates";
import { errorMessage } from "@/lib/api/errors";
import { routes } from "@/lib/routes";

/**
 * Everything ever written, newest first, searchable.
 *
 * Applying for the same kind of role twice is normal, and the version written in March is often
 * the right starting point in June. Nothing is thrown away, so nobody has to rebuild a resume
 * they already had.
 */
export function HistoryView() {
  const history = useHistory();
  const [query, setQuery] = useState("");

  const entries = history.data;
  const found = useMemo(() => {
    const all = entries ?? [];
    const needle = query.trim().toLowerCase();
    if (!needle) return all;
    return all.filter((entry) =>
      [entry.resume_title, entry.target_role ?? "", entry.label, templateInfo(entry.template).name]
        .join(" ")
        .toLowerCase()
        .includes(needle),
    );
  }, [entries, query]);

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="font-heading text-4xl tracking-tight sm:text-5xl">History</h1>
        <p className="max-w-prose leading-relaxed text-muted-foreground">
          Every resume and letter you have written here, newest first. Applying for the same kind of
          role again? Start from the one you already had.
        </p>
      </header>

      {history.isError ? (
        <LoadFailure
          error={history.error}
          onRetry={() => void history.refetch()}
          retrying={history.isRefetching}
          title="We couldn't load your history"
        />
      ) : history.isPending ? (
        <Skeleton className="h-64 rounded-xl" />
      ) : (entries ?? []).length === 0 ? (
        <p className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
          Nothing written yet. Whatever you write will be kept here.
        </p>
      ) : (
        <>
          <div className="relative max-w-sm">
            <SearchIcon
              className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              className="h-10 pl-9"
              value={query}
              placeholder="Search by role, company or name"
              aria-label="Search your history"
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>

          {found.length === 0 ? (
            <p className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
              Nothing matches “{query}”.
            </p>
          ) : (
            <ul className="divide-y rounded-xl border bg-card">
              {found.map((entry) => (
                <li
                  key={entry.version_id}
                  className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"
                >
                  <div className="min-w-0">
                    <Link
                      href={routes.resume(entry.resume_id)}
                      className="font-medium underline-offset-4 hover:underline"
                    >
                      {entry.resume_title}
                    </Link>
                    <p className="text-xs text-muted-foreground">
                      {[
                        entry.document_type === "cover_letter" ? "Cover letter" : "Resume",
                        entry.target_role,
                        templateInfo(entry.template).name,
                        entry.label,
                        new Intl.DateTimeFormat(undefined, {
                          dateStyle: "medium",
                          timeStyle: "short",
                        }).format(new Date(entry.created_at)),
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  </div>
                  <Download entry={entry} />
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

function Download({ entry }: { entry: HistoryEntry }) {
  const download = useDownloadPdf(entry.resume_id);

  return (
    <Button
      variant="outline"
      size="sm"
      disabled={download.isPending}
      onClick={() =>
        download.mutate(
          { versionId: entry.version_id, template: entry.template },
          { onError: (error) => toast.error(errorMessage(error)) },
        )
      }
    >
      {download.isPending ? <Spinner /> : <DownloadIcon aria-hidden="true" />}
      PDF
    </Button>
  );
}
