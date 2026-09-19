"use client";

import { DownloadIcon } from "lucide-react";
import { useEffect, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import type { ResumeTemplate, ResumeVersionSummary } from "@/features/resumes/api";
import { useDownloadPdf, usePreviewHtml, useVersions } from "@/features/resumes/hooks";
import { templateInfo } from "@/features/resumes/templates";
import { errorMessage } from "@/lib/api/errors";
import { cn } from "@/lib/utils";

export function VersionPanel({
  resumeId,
  selectedId,
  onSelect,
  template,
}: {
  resumeId: string;
  selectedId: string | null;
  onSelect: (versionId: string) => void;
  /** Shown in this template rather than the one each draft was written in. */
  template?: ResumeTemplate;
}) {
  const versions = useVersions(resumeId);
  const list = versions.data ?? [];
  const current = list.find((version) => version.id === selectedId) ?? list[0];

  // Follow the newest draft when one arrives and nothing is chosen yet.
  useEffect(() => {
    if (!selectedId && current) onSelect(current.id);
  }, [selectedId, current, onSelect]);

  if (versions.isPending) return <Skeleton className="h-64 rounded-xl" />;
  if (list.length === 0) return null;

  return (
    <section aria-labelledby="drafts-heading" className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="drafts-heading" className="font-heading text-xl">
          Drafts
        </h2>
        {current ? (
          <DownloadButton resumeId={resumeId} version={current} template={template} />
        ) : null}
      </div>

      <ul className="flex flex-wrap gap-2">
        {list.map((version) => {
          const selected = version.id === current?.id;
          return (
            <li key={version.id}>
              <button
                type="button"
                aria-current={selected ? "true" : undefined}
                onClick={() => onSelect(version.id)}
                className={cn(
                  "rounded-lg border px-3 py-2 text-left text-sm transition-colors outline-none",
                  "focus-visible:ring-3 focus-visible:ring-ring/50",
                  selected ? "border-primary bg-accent" : "hover:bg-muted/60",
                )}
              >
                <span className="block font-medium">{version.label}</span>
                <span className="block text-xs text-muted-foreground">
                  {templateInfo(version.template).name} ·{" "}
                  {new Intl.DateTimeFormat(undefined, {
                    dateStyle: "medium",
                    timeStyle: "short",
                  }).format(new Date(version.created_at))}
                </span>
              </button>
            </li>
          );
        })}
      </ul>

      {current ? <Preview resumeId={resumeId} versionId={current.id} template={template} /> : null}
    </section>
  );
}

function DownloadButton({
  resumeId,
  version,
  template,
}: {
  resumeId: string;
  version: ResumeVersionSummary;
  template?: ResumeTemplate;
}) {
  const download = useDownloadPdf(resumeId);

  return (
    <Button
      variant="outline"
      disabled={download.isPending}
      onClick={() => {
        download.mutate(
          { versionId: version.id, template },
          {
            onError: (error) => toast.error(errorMessage(error)),
          },
        );
      }}
    >
      {download.isPending ? <Spinner /> : <DownloadIcon aria-hidden="true" />}
      {download.isPending ? "Preparing…" : "Download PDF"}
    </Button>
  );
}

function Preview({
  resumeId,
  versionId,
  template,
}: {
  resumeId: string;
  versionId: string;
  template?: ResumeTemplate;
}) {
  const preview = usePreviewHtml(resumeId, versionId, template);
  const [height, setHeight] = useState(900);

  if (preview.isPending) return <Skeleton className="h-[900px] rounded-xl" />;
  if (preview.error) {
    return (
      <p role="alert" className="rounded-xl border border-dashed p-6 text-sm text-muted-foreground">
        {errorMessage(preview.error)}
      </p>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border bg-white">
      {/* Sandboxed: the document is inert, and cannot reach this page or the network. */}
      <iframe
        title="Resume preview"
        srcDoc={preview.data}
        sandbox=""
        className="w-full"
        style={{ height }}
        onLoad={(event) => {
          const document = event.currentTarget.contentDocument;
          if (document) setHeight(Math.max(600, document.body.scrollHeight + 32));
        }}
      />
    </div>
  );
}
