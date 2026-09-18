"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { BriefcaseIcon, PlusIcon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { LoadFailure } from "@/components/feedback/load-failure";
import { Button } from "@/components/ui/button";
import { Field, FieldDescription, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { FormErrorAlert } from "@/features/auth/components/form-alert";
import { useCreateJob, useJobs } from "@/features/jobs/hooks";
import { errorMessage } from "@/lib/api/errors";

const schema = z.object({
  title: z
    .string()
    .trim()
    .min(1, "What is the job called?")
    .max(200, "Use 200 characters or fewer"),
  company: z.string().trim().max(200, "Use 200 characters or fewer"),
  raw_text: z
    .string()
    .trim()
    .min(20, "Paste the whole advert, not just the title")
    .max(20000, "That is longer than any advert; paste the job description only"),
});

type Values = z.infer<typeof schema>;

export function JobsView() {
  const jobs = useJobs();
  const [adding, setAdding] = useState(false);

  if (jobs.isPending) return <JobsSkeleton />;
  if (jobs.isError) {
    return (
      <LoadFailure
        error={jobs.error}
        onRetry={() => void jobs.refetch()}
        retrying={jobs.isRefetching}
        title="We couldn't load your jobs"
      />
    );
  }

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div className="space-y-2">
          <h1 className="font-heading text-4xl tracking-tight sm:text-5xl">Jobs</h1>
          <p className="max-w-prose leading-relaxed text-muted-foreground">
            Paste an advert and see what your record supports, what it half supports, and what it
            doesn&apos;t mention at all. Nothing is ever added to your record for you.
          </p>
        </div>
        {!adding && jobs.data.length > 0 ? (
          <Button onClick={() => setAdding(true)}>
            <PlusIcon aria-hidden="true" />
            Add a job
          </Button>
        ) : null}
      </header>

      {adding || jobs.data.length === 0 ? <AddJobForm onCancel={() => setAdding(false)} /> : null}

      {jobs.data.length > 0 ? (
        <ul className="divide-y overflow-hidden rounded-xl border bg-card">
          {jobs.data.map((job) => (
            <li key={job.id}>
              <Link
                href={`/jobs/${job.id}`}
                className="flex items-center gap-4 px-5 py-4 outline-none transition-colors hover:bg-muted/60 focus-visible:bg-muted/60"
              >
                <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent text-accent-foreground">
                  <BriefcaseIcon className="size-4" aria-hidden="true" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{job.title}</span>
                  <span className="block truncate text-sm text-muted-foreground">
                    {job.company ?? "Company not given"} · added{" "}
                    {new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
                      new Date(job.created_at),
                    )}
                  </span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function AddJobForm({ onCancel }: { onCancel: () => void }) {
  const router = useRouter();
  const createJob = useCreateJob();
  const [formError, setFormError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { title: "", company: "", raw_text: "" },
  });

  async function onSubmit(values: Values) {
    setFormError(null);
    try {
      const job = await createJob.mutateAsync({
        title: values.title,
        company: values.company || null,
        raw_text: values.raw_text,
      });
      router.push(`/jobs/${job.id}`);
    } catch (error) {
      setFormError(errorMessage(error));
    }
  }

  return (
    <section aria-labelledby="add-job-heading" className="rounded-xl border bg-card p-5 sm:p-6">
      <h2 id="add-job-heading" className="font-heading text-xl">
        Add a job
      </h2>
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-5 space-y-5">
        <FormErrorAlert message={formError} />
        <div className="grid gap-5 sm:grid-cols-2">
          <Field data-invalid={Boolean(errors.title)}>
            <FieldLabel htmlFor="job_title">Job title</FieldLabel>
            <Input
              id="job_title"
              placeholder="Junior Backend Engineer"
              aria-invalid={Boolean(errors.title)}
              {...register("title")}
            />
            <FieldError errors={[errors.title]} />
          </Field>
          <Field data-invalid={Boolean(errors.company)}>
            <FieldLabel htmlFor="job_company">Company (optional)</FieldLabel>
            <Input
              id="job_company"
              placeholder="Northwind Logistics"
              aria-invalid={Boolean(errors.company)}
              {...register("company")}
            />
            <FieldError errors={[errors.company]} />
          </Field>
        </div>
        <Field data-invalid={Boolean(errors.raw_text)}>
          <FieldLabel htmlFor="job_advert">The advert</FieldLabel>
          <Textarea
            id="job_advert"
            rows={10}
            placeholder="Paste the whole job description here."
            aria-invalid={Boolean(errors.raw_text)}
            {...register("raw_text")}
          />
          {errors.raw_text ? (
            <FieldError errors={[errors.raw_text]} />
          ) : (
            <FieldDescription>
              Kept exactly as you paste it, so you can always see what you applied to.
            </FieldDescription>
          )}
        </Field>
        <div className="flex justify-end gap-3">
          <Button type="button" variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null}
            {isSubmitting ? "Reading the advert…" : "Save and analyse"}
          </Button>
        </div>
      </form>
    </section>
  );
}

function JobsSkeleton() {
  return (
    <div className="space-y-8" aria-busy="true" aria-label="Loading your jobs">
      <Skeleton className="h-12 w-48" />
      <Skeleton className="h-48 rounded-xl" />
    </div>
  );
}
