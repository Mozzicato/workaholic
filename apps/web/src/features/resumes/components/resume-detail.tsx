"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowLeftIcon, Trash2Icon } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { LoadFailure } from "@/components/feedback/load-failure";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldError, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { FormErrorAlert } from "@/features/auth/components/form-alert";
import { useProfile } from "@/features/profile/hooks";
import type { Resume } from "@/features/resumes/api";
import { GeneratePanel } from "@/features/resumes/components/generate-panel";
import { VersionPanel } from "@/features/resumes/components/version-panel";
import { useDeleteResume, useResume, useUpdateResume, useVersions } from "@/features/resumes/hooks";
import { ApiError, errorMessage } from "@/lib/api/errors";
import { routes } from "@/lib/routes";

const STATUS_COPY: Record<Resume["status"], { label: string; detail: string }> = {
  draft: {
    label: "Draft",
    detail: "Nothing has been written yet. Your record is what a draft will be built from.",
  },
  generating: {
    label: "Generating",
    detail: "Workaholic is writing this resume.",
  },
  ready: {
    label: "Ready",
    detail: "This resume has content you can review.",
  },
  failed: {
    label: "Needs attention",
    detail: "The last attempt didn't finish. Nothing was saved to this resume.",
  },
};

export function ResumeDetail({ id }: { id: string }) {
  const resume = useResume(id);

  if (resume.isPending) return <DetailSkeleton />;

  if (resume.error) {
    if (resume.error instanceof ApiError && resume.error.status === 404) {
      return <NotFound />;
    }
    return (
      <LoadFailure
        error={resume.error}
        onRetry={() => void resume.refetch()}
        retrying={resume.isRefetching}
        title="We couldn't load this resume"
      />
    );
  }

  return <Loaded resume={resume.data} />;
}

function Loaded({ resume }: { resume: Resume }) {
  const status = STATUS_COPY[resume.status];
  const profile = useProfile();
  const versions = useVersions(resume.id);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const recordItems = profile.data
    ? profile.data.experience.length + profile.data.projects.length + profile.data.skills.length
    : 0;

  return (
    <div className="space-y-8">
      <div>
        <Link
          href={routes.dashboard}
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeftIcon className="size-4" aria-hidden="true" />
          All resumes
        </Link>
      </div>

      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="space-y-2">
          <h1 className="font-heading text-4xl tracking-tight sm:text-5xl">{resume.title}</h1>
          <p className="text-muted-foreground">
            {resume.target_role ? `For ${resume.target_role}` : "No target role set"} · created{" "}
            {new Intl.DateTimeFormat(undefined, { dateStyle: "long" }).format(
              new Date(resume.created_at),
            )}
          </p>
        </div>
        <Badge variant={resume.status === "ready" ? "default" : "secondary"}>{status.label}</Badge>
      </header>

      <section aria-labelledby="status-heading" className="rounded-xl border bg-card p-5 sm:p-6">
        <h2 id="status-heading" className="font-heading text-xl">
          {status.label}
        </h2>
        <p className="mt-1 max-w-prose text-sm leading-relaxed text-muted-foreground">
          {status.detail}
        </p>
        <p className="mt-4 max-w-prose text-sm leading-relaxed">
          {recordItems > 0
            ? `Your career record holds ${recordItems} item${recordItems === 1 ? "" : "s"}. A resume will only ever use what's in there.`
            : "Your career record is empty. Add your experience first — a resume can only use what you've told Workaholic."}
        </p>
        <Link
          href={routes.profile}
          className="mt-4 inline-flex text-sm underline underline-offset-4 hover:text-foreground"
        >
          {recordItems > 0 ? "Review your career record" : "Add your experience"}
        </Link>
      </section>

      <GeneratePanel
        resumeId={resume.id}
        hasVersions={(versions.data?.length ?? 0) > 0}
        onGenerated={setSelectedVersionId}
      />

      <VersionPanel
        resumeId={resume.id}
        selectedId={selectedVersionId}
        onSelect={setSelectedVersionId}
      />

      <DetailsForm resume={resume} />

      <DangerZone resume={resume} />
    </div>
  );
}

const schema = z.object({
  title: z
    .string()
    .trim()
    .min(1, "Give this resume a name")
    .max(120, "Use 120 characters or fewer"),
  target_role: z.string().trim().max(120, "Use 120 characters or fewer"),
});

type Values = z.infer<typeof schema>;

function DetailsForm({ resume }: { resume: Resume }) {
  const updateResume = useUpdateResume(resume.id);
  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: resume.title,
      target_role: resume.target_role ?? "",
    },
  });

  useEffect(() => {
    reset({ title: resume.title, target_role: resume.target_role ?? "" });
  }, [resume, reset]);

  async function onSubmit(values: Values) {
    try {
      await updateResume.mutateAsync({
        title: values.title,
        target_role: values.target_role.trim() || null,
      });
      toast.success("Resume updated");
    } catch (error) {
      setError("root", {
        message:
          error instanceof ApiError && error.status === 409
            ? "You already have a resume with that name."
            : errorMessage(error),
      });
    }
  }

  return (
    <section aria-labelledby="details-heading" className="rounded-xl border bg-card p-5 sm:p-6">
      <h2 id="details-heading" className="font-heading text-xl">
        Details
      </h2>
      <form onSubmit={handleSubmit(onSubmit)} noValidate className="mt-5 space-y-5">
        <FormErrorAlert message={errors.root?.message ?? null} />
        <div className="grid gap-5 sm:grid-cols-2">
          <Field data-invalid={Boolean(errors.title)}>
            <FieldLabel htmlFor="resume_title">Name</FieldLabel>
            <Input id="resume_title" aria-invalid={Boolean(errors.title)} {...register("title")} />
            <FieldError errors={[errors.title]} />
          </Field>
          <Field data-invalid={Boolean(errors.target_role)}>
            <FieldLabel htmlFor="resume_target_role">Target role</FieldLabel>
            <Input
              id="resume_target_role"
              placeholder="Junior Backend Engineer"
              aria-invalid={Boolean(errors.target_role)}
              {...register("target_role")}
            />
            <FieldError errors={[errors.target_role]} />
          </Field>
        </div>
        <div className="flex justify-end">
          <Button type="submit" disabled={isSubmitting || !isDirty}>
            {isSubmitting ? <Spinner /> : null}
            {isSubmitting ? "Saving…" : "Save changes"}
          </Button>
        </div>
      </form>
    </section>
  );
}

function DangerZone({ resume }: { resume: Resume }) {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const deleteResume = useDeleteResume();
  const router = useRouter();

  async function onConfirm() {
    setError(null);
    try {
      await deleteResume.mutateAsync(resume.id);
      toast.success(`${resume.title} deleted`);
      router.push(routes.dashboard);
    } catch (failure) {
      setError(errorMessage(failure));
    }
  }

  return (
    <section
      aria-labelledby="delete-heading"
      className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-destructive/25 p-5 sm:p-6"
    >
      <div className="space-y-1">
        <h2 id="delete-heading" className="font-medium">
          Delete this resume
        </h2>
        <p className="text-sm text-muted-foreground">
          Your career record is kept. Only this resume goes.
        </p>
      </div>
      <Button variant="outline" onClick={() => setOpen(true)}>
        <Trash2Icon aria-hidden="true" />
        Delete
      </Button>

      <Dialog
        open={open}
        onOpenChange={(next) => {
          setOpen(next);
          if (!next) setError(null);
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="font-heading text-2xl">Delete {resume.title}?</DialogTitle>
            <DialogDescription>
              This can&apos;t be undone. Your career record and any other resumes stay as they are.
            </DialogDescription>
          </DialogHeader>
          <FormErrorAlert message={error} />
          <DialogFooter showCloseButton>
            <Button
              variant="destructive"
              onClick={() => void onConfirm()}
              disabled={deleteResume.isPending}
            >
              {deleteResume.isPending ? <Spinner /> : null}
              {deleteResume.isPending ? "Deleting…" : "Delete resume"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}

function NotFound() {
  return (
    <div className="mx-auto max-w-md py-16 text-center">
      <h1 className="font-heading text-4xl tracking-tight">This resume isn&apos;t here.</h1>
      <p className="mt-3 text-muted-foreground">
        It may have been deleted, or the link may belong to someone else.
      </p>
      <Link
        href={routes.dashboard}
        className="mt-8 inline-flex text-sm underline underline-offset-4"
      >
        Back to your resumes
      </Link>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="space-y-8" aria-busy="true" aria-label="Loading this resume">
      <Skeleton className="h-4 w-28" />
      <Skeleton className="h-12 w-80" />
      <Skeleton className="h-40 rounded-xl" />
      <Skeleton className="h-56 rounded-xl" />
    </div>
  );
}
