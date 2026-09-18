"use client";

import { GaugeIcon, ShuffleIcon } from "lucide-react";
import Link from "next/link";
import { useId, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useJobs } from "@/features/jobs/hooks";
import type { AtsReport, ChangeSummary } from "@/features/resumes/api";
import { useAtsReport, useTailor } from "@/features/resumes/hooks";
import { errorMessage } from "@/lib/api/errors";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

/** Tailoring and the ATS check, for the draft currently selected. Resumes only. */
export function ResumeTools({
  resumeId,
  versionId,
  onTailored,
}: {
  resumeId: string;
  versionId: string;
  onTailored: (versionId: string) => void;
}) {
  const jobs = useJobs();
  const [jobId, setJobId] = useState<string>("");
  const selectId = useId();
  const hasJobs = (jobs.data?.length ?? 0) > 0;

  return (
    <section
      aria-labelledby="tools-heading"
      className="space-y-5 rounded-xl border bg-card p-5 sm:p-6"
    >
      <div className="space-y-1">
        <h2 id="tools-heading" className="font-heading text-xl">
          Check and tailor this draft
        </h2>
        <p className="max-w-prose text-sm leading-relaxed text-muted-foreground">
          Pick a job to measure against. Tailoring only changes the order things appear in — never a
          word of what they say, and never adds what your record doesn&apos;t hold.
        </p>
      </div>

      {hasJobs ? (
        <div className="space-y-1.5">
          <label htmlFor={selectId} className="text-sm font-medium">
            Job
          </label>
          <select
            id={selectId}
            value={jobId}
            onChange={(event) => setJobId(event.target.value)}
            className="block h-9 w-full max-w-md rounded-md border bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            <option value="">No job — check the draft on its own</option>
            {jobs.data?.map((job) => (
              <option key={job.id} value={job.id}>
                {job.title}
                {job.company ? ` — ${job.company}` : ""}
              </option>
            ))}
          </select>
        </div>
      ) : (
        <p className="text-sm text-muted-foreground">
          <Link href={routes.jobs} className="underline underline-offset-4 hover:text-foreground">
            Add a job
          </Link>{" "}
          to tailor this draft to it and check it against the advert&apos;s keywords.
        </p>
      )}

      <Ats resumeId={resumeId} versionId={versionId} jobId={jobId || null} />
      {jobId ? (
        <Tailor resumeId={resumeId} versionId={versionId} jobId={jobId} onTailored={onTailored} />
      ) : null}
    </section>
  );
}

function Ats({
  resumeId,
  versionId,
  jobId,
}: {
  resumeId: string;
  versionId: string;
  jobId: string | null;
}) {
  const report = useAtsReport(resumeId, versionId, jobId);

  return (
    <div className="space-y-4 border-t pt-5">
      <Button variant="outline" disabled={report.isFetching} onClick={() => void report.refetch()}>
        {report.isFetching ? <Spinner /> : <GaugeIcon aria-hidden="true" />}
        {report.isFetching ? "Checking…" : "Check ATS compatibility"}
      </Button>
      {report.isError ? (
        <p role="alert" className="text-sm text-destructive">
          {errorMessage(report.error)}
        </p>
      ) : null}
      {report.data ? <AtsResult report={report.data} /> : null}
    </div>
  );
}

function AtsResult({ report }: { report: AtsReport }) {
  const failed = report.checks.filter((check) => !check.passed);
  return (
    <div className="space-y-4">
      <div>
        <p className="text-sm text-muted-foreground">Workaholic ATS Compatibility Score</p>
        <p className="font-heading text-4xl">
          {report.score}
          <span className="text-xl text-muted-foreground">/{report.maximum}</span>
        </p>
      </div>

      <ul className="space-y-3">
        {report.categories.map((category) => (
          <li key={category.category} className="space-y-1">
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className="font-medium">{category.category}</span>
              <span className="text-muted-foreground">
                {category.score}/{category.maximum}
              </span>
            </div>
            <div
              className="h-1.5 overflow-hidden rounded-full bg-muted"
              role="img"
              aria-label={`${category.category}: ${category.score} of ${category.maximum}`}
            >
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${(100 * category.score) / category.maximum}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">{category.explanation}</p>
          </li>
        ))}
      </ul>

      {failed.length > 0 ? (
        <div className="space-y-2">
          <h3 className="text-sm font-medium">Worth looking at</h3>
          <ul className="space-y-1.5 text-sm">
            {failed.map((check) => (
              <li key={check.name}>
                <span className="font-medium">{check.name}.</span>{" "}
                <span className="text-muted-foreground">{check.detail}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {/* PRD §35: the score is always shown with what it is not. */}
      <p className="rounded-lg bg-muted/60 p-3 text-xs leading-relaxed text-muted-foreground">
        {report.caveat}
      </p>
    </div>
  );
}

function Tailor({
  resumeId,
  versionId,
  jobId,
  onTailored,
}: {
  resumeId: string;
  versionId: string;
  jobId: string;
  onTailored: (versionId: string) => void;
}) {
  const tailor = useTailor(resumeId);
  const [summary, setSummary] = useState<ChangeSummary | null>(null);

  return (
    <div className="space-y-4 border-t pt-5">
      <Button
        disabled={tailor.isPending}
        onClick={() =>
          tailor.mutate(
            { versionId, jobId },
            {
              onSuccess: (result) => {
                setSummary(result.summary);
                toast.success(`${result.version.label} tailored`);
                onTailored(result.version.id);
              },
              onError: (error) => toast.error(errorMessage(error)),
            },
          )
        }
      >
        {tailor.isPending ? <Spinner /> : <ShuffleIcon aria-hidden="true" />}
        Tailor a copy to this job
      </Button>
      {summary ? <Summary summary={summary} /> : null}
    </div>
  );
}

function Summary({ summary }: { summary: ChangeSummary }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      <SummaryList title="Changed" items={summary.changed} />
      <SummaryList title="Not changed" items={summary.unchanged} />
      {summary.missing_requirements.length > 0 ? (
        <div className="space-y-1.5 sm:col-span-2">
          <h3 className="text-sm font-medium">
            The job asks for, and your record doesn&apos;t hold
          </h3>
          <p className="text-sm text-muted-foreground">
            {summary.missing_requirements.join(", ")}. These were not added. If any are true of you,
            add them to your record first.
          </p>
        </div>
      ) : null}
    </div>
  );
}

function SummaryList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="space-y-1.5">
      <h3 className="text-sm font-medium">{title}</h3>
      <ul className={cn("list-disc space-y-1 pl-4 text-sm text-muted-foreground")}>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
