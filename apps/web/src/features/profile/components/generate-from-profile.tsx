"use client";

import { SparklesIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { useCreateJob } from "@/features/jobs/hooks";
import { ReadinessChecklist } from "@/features/profile/components/readiness-checklist";
import { useReadiness } from "@/features/profile/hooks";
import type { ResumeTemplate } from "@/features/resumes/api";
import { TemplateGallery } from "@/features/resumes/components/template-gallery";
import { useCreateResume } from "@/features/resumes/hooks";
import { getApiClient } from "@/lib/api/browser";
import { generateVersion, tailorVersion } from "@/features/resumes/api";
import { ApiError, errorMessage } from "@/lib/api/errors";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

type Kind = "general" | "tailored";

/**
 * Write the resume from here, where the record is.
 *
 * Somebody filling in their details should not have to find another page to get the thing they
 * came for. Two kinds: one that spreads everything they have, and one aimed at a job they paste
 * in. Both are written from this record and nothing else.
 */
export function GenerateFromProfile() {
  const readiness = useReadiness();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<Kind>("general");
  const [template, setTemplate] = useState<ResumeTemplate>("classic");
  const [role, setRole] = useState("");
  const [company, setCompany] = useState("");
  const [advert, setAdvert] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const createResume = useCreateResume();
  const createJob = useCreateJob();
  // Until the check comes back, say nothing about the record: telling somebody their record is
  // short and then correcting yourself half a second later is worse than waiting.
  const checking = readiness.isPending;
  const ready = readiness.data?.resume_ready ?? false;

  async function onGenerate() {
    const api = getApiClient();
    try {
      let jobId: string | null = null;
      if (kind === "tailored") {
        setBusy("Reading the job advert…");
        const job = await createJob.mutateAsync({
          title: role.trim() || "Untitled role",
          company: company.trim() || null,
          raw_text: advert.trim(),
        });
        jobId = job.id;
      }

      setBusy("Writing your resume…");
      const title =
        kind === "general"
          ? "General resume"
          : [role.trim() || "Role", company.trim()].filter(Boolean).join(" — ");
      const resume = await createResume.mutateAsync({
        title,
        target_role: kind === "tailored" ? role.trim() || null : null,
        template,
      });
      const version = await generateVersion(api, resume.id);

      if (jobId) {
        setBusy("Leading with what the job asks for…");
        await tailorVersion(api, resume.id, version.id, jobId);
      }
      setOpen(false);
      router.push(routes.resume(resume.id));
    } catch (error) {
      if (error instanceof ApiError && error.status === 409) {
        toast.error("You already have a resume with that name. Rename it, or change the role.");
      } else {
        toast.error(errorMessage(error));
      }
    } finally {
      setBusy(null);
    }
  }

  return (
    <section
      aria-labelledby="generate-heading"
      className="rounded-xl border border-primary/30 bg-accent/30 p-5 sm:p-6"
    >
      <h2 id="generate-heading" className="font-heading text-xl">
        {checking ? "Your resume" : ready ? "Ready to write your resume" : "Not quite ready yet"}
      </h2>
      <p className="mt-1 max-w-prose text-sm leading-relaxed text-muted-foreground">
        {checking
          ? "Checking what your record holds…"
          : ready
            ? "Everything on this page is what a resume can say. Write one that covers all of it, or one aimed at a job you are applying for."
            : "A resume written from this would be missing things employers look for first. Here is what it still needs."}
      </p>

      {readiness.data && !ready ? (
        <ReadinessChecklist readiness={readiness.data} className="mt-4" />
      ) : null}

      <div className="mt-5 flex flex-wrap gap-3">
        <Button
          size="lg"
          className="h-10"
          disabled={!ready || checking}
          onClick={() => setOpen(true)}
        >
          <SparklesIcon aria-hidden="true" />
          Generate my resume
        </Button>
        {!ready && !checking ? (
          <Button
            size="lg"
            variant="outline"
            className="h-10"
            onClick={() => router.push(routes.assistant)}
          >
            Answer a few questions instead
          </Button>
        ) : null}
      </div>

      <Dialog open={open} onOpenChange={(next) => (busy ? null : setOpen(next))}>
        <DialogContent className="max-h-[92dvh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle className="font-heading text-2xl">Write my resume</DialogTitle>
            <DialogDescription>
              Written from your record. Nothing is added that you have not told us.
            </DialogDescription>
          </DialogHeader>

          <fieldset>
            <legend className="text-sm font-medium">What is it for?</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {(
                [
                  {
                    value: "general" as const,
                    label: "A general resume",
                    description: "Covers everything you have. Good to have ready.",
                  },
                  {
                    value: "tailored" as const,
                    label: "For a specific job",
                    description: "Paste the advert; it leads with what that job asks for.",
                  },
                ] satisfies { value: Kind; label: string; description: string }[]
              ).map((option) => (
                <button
                  key={option.value}
                  type="button"
                  aria-pressed={kind === option.value}
                  onClick={() => setKind(option.value)}
                  className={cn(
                    "rounded-lg border px-3 py-2.5 text-left transition-colors outline-none",
                    "focus-visible:ring-3 focus-visible:ring-ring/50",
                    kind === option.value ? "border-primary bg-accent" : "hover:bg-muted/60",
                  )}
                >
                  <span className="block text-sm font-medium">{option.label}</span>
                  <span className="block text-xs text-muted-foreground">{option.description}</span>
                </button>
              ))}
            </div>
          </fieldset>

          {kind === "tailored" ? (
            <div className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <Field>
                  <FieldLabel htmlFor="target_role">Role</FieldLabel>
                  <Input
                    id="target_role"
                    value={role}
                    placeholder="Junior Frontend Engineer"
                    maxLength={120}
                    onChange={(event) => setRole(event.target.value)}
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="target_company">Company (optional)</FieldLabel>
                  <Input
                    id="target_company"
                    value={company}
                    placeholder="Northwind Payments"
                    maxLength={200}
                    onChange={(event) => setCompany(event.target.value)}
                  />
                </Field>
              </div>
              <Field>
                <FieldLabel htmlFor="advert">Paste the job advert</FieldLabel>
                <Textarea
                  id="advert"
                  rows={6}
                  value={advert}
                  maxLength={20000}
                  placeholder="Paste the whole advert. The more of it, the better the match."
                  onChange={(event) => setAdvert(event.target.value)}
                />
                <FieldDescription>
                  Used to decide what leads, and to show you what they ask for that you do not yet
                  have. It never adds a skill to your resume on your behalf.
                </FieldDescription>
              </Field>
            </div>
          ) : null}

          <TemplateGallery value={template} onChange={setTemplate} />

          <DialogFooter showCloseButton>
            <Button
              size="lg"
              className="h-10"
              disabled={Boolean(busy) || (kind === "tailored" && advert.trim().length < 40)}
              onClick={() => void onGenerate()}
            >
              {busy ? <Spinner /> : <SparklesIcon aria-hidden="true" />}
              {busy ?? "Write it"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
