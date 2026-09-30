"use client";

import {
  ArrowLeftIcon,
  CheckIcon,
  CircleDashedIcon,
  MinusIcon,
  RotateCwIcon,
  Trash2Icon,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { LoadFailure } from "@/components/feedback/load-failure";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import type { Job, RequirementMatch } from "@/features/jobs/api";
import { GapCoaching } from "@/features/jobs/components/gap-coaching";
import { useDeleteJob, useJob, useMatch, useReanalyseJob } from "@/features/jobs/hooks";
import { ApiError, errorMessage } from "@/lib/api/errors";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

export function JobDetail({ id }: { id: string }) {
  const job = useJob(id);

  if (job.isPending) return <DetailSkeleton />;
  if (job.isError) {
    if (job.error instanceof ApiError && job.error.status === 404) {
      return (
        <div className="mx-auto max-w-md py-16 text-center">
          <h1 className="font-heading text-4xl tracking-tight">This job isn&apos;t here.</h1>
          <Link
            href={routes.jobs}
            className="mt-8 inline-flex text-sm underline underline-offset-4"
          >
            Back to your jobs
          </Link>
        </div>
      );
    }
    return (
      <LoadFailure
        error={job.error}
        onRetry={() => void job.refetch()}
        retrying={job.isRefetching}
        title="We couldn't load this job"
      />
    );
  }

  return <Loaded job={job.data} />;
}

function Loaded({ job }: { job: Job }) {
  const analysed =
    job.analysis.required_skills.length > 0 || job.analysis.preferred_skills.length > 0;

  return (
    <div className="space-y-8">
      <Link
        href={routes.jobs}
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeftIcon className="size-4" aria-hidden="true" />
        All jobs
      </Link>

      <header className="space-y-2">
        <h1 className="font-heading text-4xl tracking-tight sm:text-5xl">{job.title}</h1>
        <p className="text-muted-foreground">
          {[job.company, job.analysis.seniority].filter(Boolean).join(" · ") || "Company not given"}
        </p>
      </header>

      {analysed ? <MatchSection jobId={job.id} /> : <NotAnalysed jobId={job.id} />}
      {analysed ? <GapCoaching jobId={job.id} /> : null}

      <section aria-labelledby="advert-heading" className="space-y-3">
        <h2 id="advert-heading" className="font-heading text-xl">
          The advert, as you pasted it
        </h2>
        <pre className="max-h-96 overflow-y-auto rounded-xl border bg-card p-5 font-sans text-sm leading-relaxed whitespace-pre-wrap">
          {job.raw_text}
        </pre>
      </section>

      <DeleteJob jobId={job.id} title={job.title} />
    </div>
  );
}

function MatchSection({ jobId }: { jobId: string }) {
  const report = useMatch(jobId);

  if (report.isPending) return <Skeleton className="h-64 rounded-xl" />;
  if (report.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        {errorMessage(report.error)}
      </p>
    );
  }

  const { matches, matched, partially_matched, not_found } = report.data;
  const required = matches.filter((match) => match.kind === "required");
  const preferred = matches.filter((match) => match.kind === "preferred");

  return (
    <section
      aria-labelledby="match-heading"
      className="space-y-5 rounded-xl border bg-card p-5 sm:p-6"
    >
      <div className="space-y-1">
        <h2 id="match-heading" className="font-heading text-xl">
          What your record supports
        </h2>
        <p className="text-sm text-muted-foreground">
          {matched} matched · {partially_matched} partly · {not_found} not in your record. This only
          reads your record — nothing is added to it, and nothing missing is filled in.
        </p>
      </div>

      <MatchList title="Required" matches={required} />
      {preferred.length > 0 ? <MatchList title="Nice to have" matches={preferred} /> : null}

      {not_found > 0 ? (
        <p className="border-t pt-4 text-sm leading-relaxed text-muted-foreground">
          If you do have experience with something marked as not in your record,{" "}
          <Link
            href={routes.profile}
            className="underline underline-offset-4 hover:text-foreground"
          >
            add it to your record
          </Link>{" "}
          first — then it can appear on a resume. If you don&apos;t, leave it off: it will come up
          in the interview.
        </p>
      ) : null}
    </section>
  );
}

const STATE_LABEL: Record<RequirementMatch["state"], string> = {
  MATCHED: "In your record",
  PARTIALLY_MATCHED: "Mentioned, not listed",
  NOT_FOUND: "Not in your record",
};

function MatchList({ title, matches }: { title: string; matches: RequirementMatch[] }) {
  if (matches.length === 0) return null;
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium">{title}</h3>
      <ul className="space-y-2">
        {matches.map((match) => (
          <li key={match.requirement} className="flex items-start gap-3">
            <StateIcon state={match.state} />
            <div className="min-w-0 flex-1">
              <p className="text-sm">
                <span className="font-medium">{match.requirement}</span>
                <span className="text-muted-foreground"> — {STATE_LABEL[match.state]}</span>
              </p>
              {match.evidence.length > 0 ? (
                <p className="truncate text-xs text-muted-foreground">
                  From your record: &ldquo;{match.evidence[0]}&rdquo;
                </p>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

function StateIcon({ state }: { state: RequirementMatch["state"] }) {
  const Icon =
    state === "MATCHED" ? CheckIcon : state === "PARTIALLY_MATCHED" ? CircleDashedIcon : MinusIcon;
  return (
    <span
      aria-hidden="true"
      className={cn(
        "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full",
        state === "MATCHED" && "bg-primary text-primary-foreground",
        state === "PARTIALLY_MATCHED" && "bg-accent text-accent-foreground",
        state === "NOT_FOUND" && "bg-muted text-muted-foreground",
      )}
    >
      <Icon className="size-3" />
    </span>
  );
}

function NotAnalysed({ jobId }: { jobId: string }) {
  const reanalyse = useReanalyseJob(jobId);
  return (
    <section className="rounded-xl border border-dashed p-5 sm:p-6">
      <p className="text-sm text-muted-foreground">
        This advert hasn&apos;t been read into requirements yet — usually because the writing
        assistant was unavailable when you saved it.
      </p>
      <Button
        className="mt-4"
        variant="outline"
        disabled={reanalyse.isPending}
        onClick={() =>
          reanalyse.mutate(undefined, { onError: (error) => toast.error(errorMessage(error)) })
        }
      >
        {reanalyse.isPending ? <Spinner /> : <RotateCwIcon aria-hidden="true" />}
        Read it now
      </Button>
    </section>
  );
}

function DeleteJob({ jobId, title }: { jobId: string; title: string }) {
  const remove = useDeleteJob();
  const router = useRouter();
  return (
    <div className="flex justify-end">
      <Button
        variant="ghost"
        disabled={remove.isPending}
        onClick={() =>
          remove.mutate(jobId, {
            onSuccess: () => {
              toast.success(`${title} removed`);
              router.push(routes.jobs);
            },
            onError: (error) => toast.error(errorMessage(error)),
          })
        }
      >
        <Trash2Icon aria-hidden="true" />
        Remove this job
      </Button>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-8" aria-busy="true" aria-label="Loading this job">
      <Skeleton className="h-12 w-72" />
      <Skeleton className="h-64 rounded-xl" />
    </div>
  );
}
