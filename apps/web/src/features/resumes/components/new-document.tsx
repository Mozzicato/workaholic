"use client";

import { useState } from "react";

import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useCreateJob } from "@/features/jobs/hooks";
import { generateVersion, tailorVersion, type ResumeTemplate } from "@/features/resumes/api";
import { useCreateResume } from "@/features/resumes/hooks";
import { getApiClient } from "@/lib/api/browser";
import { ApiError } from "@/lib/api/errors";
import { cn } from "@/lib/utils";

/**
 * Starting a document, wherever it is started from.
 *
 * There is one flow and both entry points use it, because a person who starts from their record
 * and a person who starts from their resumes are doing the same thing and should be asked the
 * same questions.
 */

export type Purpose = "general" | "tailored";

export type NewDocument = {
  purpose: Purpose;
  template: ResumeTemplate;
  role: string;
  company: string;
  advert: string;
};

export const BLANK: NewDocument = {
  purpose: "general",
  template: "classic",
  role: "",
  company: "",
  advert: "",
};

/** Enough of an advert to be worth reading. A job title alone tailors nothing. */
export const MIN_ADVERT = 40;

export function describes(document: NewDocument): boolean {
  return document.purpose === "general" || document.advert.trim().length >= MIN_ADVERT;
}

function titleFor(document: NewDocument): string {
  if (document.purpose === "general") return "General resume";
  return (
    [document.role.trim() || "Role", document.company.trim()].filter(Boolean).join(" — ") ||
    "Resume"
  );
}

/**
 * Creates the resume, writes it, and — when it is for a job — leads with what that job asks for.
 * Returns the resume's id so the caller can open it.
 */
export function useWriteDocument() {
  const createResume = useCreateResume();
  const createJob = useCreateJob();
  const [step, setStep] = useState<string | null>(null);

  async function write(document: NewDocument): Promise<string> {
    const api = getApiClient();
    try {
      let jobId: string | null = null;
      if (document.purpose === "tailored") {
        setStep("Reading the job advert…");
        const job = await createJob.mutateAsync({
          title: document.role.trim() || "Untitled role",
          company: document.company.trim() || null,
          raw_text: document.advert.trim(),
        });
        jobId = job.id;
      }

      setStep("Writing your resume…");
      const resume = await createWithFreeName(document, createResume.mutateAsync);
      const version = await generateVersion(api, resume.id);

      if (jobId) {
        setStep("Leading with what the job asks for…");
        await tailorVersion(api, resume.id, version.id, jobId);
      }
      return resume.id;
    } finally {
      setStep(null);
    }
  }

  return { write, step };
}

/** Two resumes for the same role are normal; a name clash should not stop one being written. */
async function createWithFreeName(
  document: NewDocument,
  create: (body: {
    title: string;
    target_role?: string | null;
    template?: ResumeTemplate;
  }) => Promise<{ id: string }>,
): Promise<{ id: string }> {
  const base = titleFor(document);
  for (let attempt = 1; attempt <= 20; attempt += 1) {
    try {
      return await create({
        title: attempt === 1 ? base : `${base} (${attempt})`,
        target_role: document.purpose === "tailored" ? document.role.trim() || null : null,
        template: document.template,
      });
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 409)) throw error;
    }
  }
  throw new ApiError({
    status: 409,
    code: "CONFLICT",
    message: "You have a lot of resumes with that name. Rename one and try again.",
  });
}

/** "What is it for?" — the question that decides whether a job advert is read. */
export function PurposeChooser({
  value,
  onChange,
}: {
  value: NewDocument;
  onChange: (next: NewDocument) => void;
}) {
  const options = [
    {
      purpose: "general" as const,
      label: "A general resume",
      description: "Covers everything you have. Good to have ready.",
    },
    {
      purpose: "tailored" as const,
      label: "For a specific job",
      description: "Paste the advert; it leads with what that job asks for.",
    },
  ];

  return (
    <div className="space-y-4">
      <fieldset>
        <legend className="text-sm font-medium">What is it for?</legend>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {options.map((option) => (
            <button
              key={option.purpose}
              type="button"
              aria-pressed={value.purpose === option.purpose}
              onClick={() => onChange({ ...value, purpose: option.purpose })}
              className={cn(
                "rounded-lg border px-3 py-2.5 text-left transition-colors outline-none",
                "focus-visible:ring-3 focus-visible:ring-ring/50",
                value.purpose === option.purpose ? "border-primary bg-accent" : "hover:bg-muted/60",
              )}
            >
              <span className="block text-sm font-medium">{option.label}</span>
              <span className="block text-xs text-muted-foreground">{option.description}</span>
            </button>
          ))}
        </div>
      </fieldset>

      {value.purpose === "tailored" ? (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="target_role">Role</FieldLabel>
              <Input
                id="target_role"
                value={value.role}
                placeholder="Junior Frontend Engineer"
                maxLength={120}
                onChange={(event) => onChange({ ...value, role: event.target.value })}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="target_company">Company (optional)</FieldLabel>
              <Input
                id="target_company"
                value={value.company}
                placeholder="Northwind Payments"
                maxLength={200}
                onChange={(event) => onChange({ ...value, company: event.target.value })}
              />
            </Field>
          </div>
          <Field>
            <FieldLabel htmlFor="advert">Paste the job advert</FieldLabel>
            <Textarea
              id="advert"
              rows={6}
              value={value.advert}
              maxLength={20000}
              placeholder="Paste the whole advert. The more of it, the better the match."
              onChange={(event) => onChange({ ...value, advert: event.target.value })}
            />
            <FieldDescription>
              Used to decide what leads, and to show you what they ask for that you do not yet have.
              It never adds a skill to your resume on your behalf.
            </FieldDescription>
          </Field>
        </div>
      ) : null}
    </div>
  );
}
