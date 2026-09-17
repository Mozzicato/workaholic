"use client";

import { FileTextIcon } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { CreateResumeDialog } from "@/features/resumes/components/create-resume-dialog";
import type { Resume } from "@/features/resumes/api";

const STATUS_LABELS: Record<Resume["status"], string> = {
  draft: "Draft",
  generating: "Generating",
  ready: "Ready",
  failed: "Needs attention",
};

export function ResumeList({ resumes }: { resumes: Resume[] }) {
  if (resumes.length === 0) {
    return <EmptyState />;
  }

  return (
    <ul className="divide-y overflow-hidden rounded-xl border bg-card">
      {resumes.map((resume) => (
        <li key={resume.id}>
          <Link
            href={`/resumes/${resume.id}`}
            className="flex items-center gap-4 px-5 py-4 outline-none transition-colors hover:bg-muted/60 focus-visible:bg-muted/60"
          >
            <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
              <FileTextIcon className="size-4" aria-hidden="true" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate font-medium">{resume.title}</span>
              <span className="block truncate text-sm text-muted-foreground">
                {resume.target_role ?? "No target role yet"} · updated{" "}
                {new Intl.DateTimeFormat(undefined, {
                  dateStyle: "medium",
                }).format(new Date(resume.updated_at))}
              </span>
            </span>
            <Badge variant={resume.status === "ready" ? "default" : "secondary"}>
              {STATUS_LABELS[resume.status]}
            </Badge>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function EmptyState() {
  return (
    <div className="rounded-xl border border-dashed bg-card px-6 py-12 text-center sm:px-10">
      <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-accent text-accent-foreground">
        <FileTextIcon className="size-5" aria-hidden="true" />
      </div>
      <p className="mt-5 font-heading text-2xl">You haven&apos;t created a resume yet.</p>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">
        Start one, then tell Workaholic what you&apos;ve actually done. Everything on the page will
        trace back to something you said.
      </p>
      <div className="mt-6 flex justify-center">
        <CreateResumeDialog />
      </div>
    </div>
  );
}
