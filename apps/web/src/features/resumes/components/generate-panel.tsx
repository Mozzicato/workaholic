"use client";

import { SparklesIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { DocumentType, ResumeTemplate } from "@/features/resumes/api";
import { useGenerateVersion } from "@/features/resumes/hooks";
import { ApiError, errorMessage } from "@/lib/api/errors";
import { cn } from "@/lib/utils";

/** Refusals the user can act on. Anything else is a failure, and is reported as one. */
const REFUSAL_TITLES: Record<string, string> = {
  GENERATION_BLOCKED: "Draft refused",
  PROFILE_INCOMPLETE: "Nothing to write from yet",
  PROFILE_CONTAINS_INSTRUCTIONS: "Some lines need rewriting",
};
const REFUSAL_CODES = new Set(Object.keys(REFUSAL_TITLES));

const TEMPLATES: { value: ResumeTemplate; label: string; description: string }[] = [
  { value: "standard", label: "Standard", description: "Roomy and conventional" },
  { value: "compact", label: "Compact", description: "Fits more on one page" },
  { value: "academic", label: "Academic", description: "Education first" },
];

export function GeneratePanel({
  resumeId,
  documentType,
  targetRole,
  hasVersions,
  onGenerated,
}: {
  resumeId: string;
  documentType: DocumentType;
  targetRole: string | null;
  hasVersions: boolean;
  onGenerated: (versionId: string) => void;
}) {
  const isLetter = documentType === "cover_letter";
  const [template, setTemplate] = useState<ResumeTemplate>("standard");
  const [brief, setBrief] = useState({ company: "", hiring_manager: "", job_advert: "" });
  const [blocked, setBlocked] = useState<{
    title: string;
    message: string;
    problems: string[];
  } | null>(null);
  const generate = useGenerateVersion(resumeId);

  async function onGenerate() {
    setBlocked(null);
    try {
      const version = await generate.mutateAsync({
        template,
        brief: isLetter
          ? {
              company: brief.company.trim(),
              role: targetRole,
              hiring_manager: brief.hiring_manager.trim() || null,
              job_advert: brief.job_advert.trim() || null,
            }
          : undefined,
      });
      toast.success(`${version.label} written`);
      onGenerated(version.id);
    } catch (error) {
      if (error instanceof ApiError && REFUSAL_CODES.has(error.code)) {
        setBlocked({
          title: REFUSAL_TITLES[error.code] ?? "Draft refused",
          message: error.message,
          problems: error.details.map((detail) =>
            error.code === "PROFILE_CONTAINS_INSTRUCTIONS" ? `"${detail.issue}"` : detail.issue,
          ),
        });
        return;
      }
      toast.error(errorMessage(error));
    }
  }

  return (
    <section aria-labelledby="write-heading" className="rounded-xl border bg-card p-5 sm:p-6">
      <h2 id="write-heading" className="font-heading text-xl">
        {hasVersions ? "Write another draft" : isLetter ? "Write this letter" : "Write this resume"}
      </h2>
      <p className="mt-1 max-w-prose text-sm leading-relaxed text-muted-foreground">
        {isLetter
          ? "The advert decides which of your experience leads. It never adds to it: if the letter would claim something you haven't told us, it's refused instead."
          : "Workaholic rewrites what you recorded so it reads well. It never adds a number, a tool or an employer you didn't mention — if the wording would go beyond your record, the draft is refused instead."}
      </p>

      {isLetter ? (
        <div className="mt-5 space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field>
              <FieldLabel htmlFor="company">Company</FieldLabel>
              <Input
                id="company"
                value={brief.company}
                placeholder="Northwind Logistics"
                maxLength={200}
                onChange={(event) =>
                  setBrief((current) => ({ ...current, company: event.target.value }))
                }
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="hiring_manager">Addressed to (optional)</FieldLabel>
              <Input
                id="hiring_manager"
                value={brief.hiring_manager}
                placeholder="A name, if you have one"
                maxLength={120}
                onChange={(event) =>
                  setBrief((current) => ({ ...current, hiring_manager: event.target.value }))
                }
              />
            </Field>
          </div>
          <Field>
            <FieldLabel htmlFor="job_advert">The advert (optional)</FieldLabel>
            <Textarea
              id="job_advert"
              rows={4}
              value={brief.job_advert}
              placeholder="Paste the job description here."
              maxLength={6000}
              onChange={(event) =>
                setBrief((current) => ({ ...current, job_advert: event.target.value }))
              }
            />
            <FieldDescription>
              Used to decide what to lead with — never to claim anything on your behalf.
            </FieldDescription>
          </Field>
        </div>
      ) : (
        <fieldset className="mt-5">
          <legend className="text-sm font-medium">Template</legend>
          <div className="mt-2 grid gap-2 sm:grid-cols-3">
            {TEMPLATES.map((option) => {
              const selected = template === option.value;
              return (
                <button
                  key={option.value}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => setTemplate(option.value)}
                  className={cn(
                    "rounded-lg border px-3 py-2.5 text-left transition-colors outline-none",
                    "focus-visible:ring-3 focus-visible:ring-ring/50",
                    selected ? "border-primary bg-accent" : "hover:bg-muted/60",
                  )}
                >
                  <span className="block text-sm font-medium">{option.label}</span>
                  <span className="block text-xs text-muted-foreground">{option.description}</span>
                </button>
              );
            })}
          </div>
        </fieldset>
      )}

      {blocked ? (
        <Alert variant="destructive" className="mt-5 border-destructive/30">
          <AlertTitle>{blocked.title}</AlertTitle>
          <AlertDescription className="space-y-2">
            <p>{blocked.message}</p>
            {blocked.problems.length > 0 ? (
              <ul className="list-disc space-y-1 pl-4">
                {blocked.problems.map((problem) => (
                  <li key={problem}>{problem}</li>
                ))}
              </ul>
            ) : null}
          </AlertDescription>
        </Alert>
      ) : null}

      <Button
        className="mt-5"
        onClick={() => void onGenerate()}
        disabled={generate.isPending || (isLetter && !brief.company.trim())}
      >
        {generate.isPending ? <Spinner /> : <SparklesIcon aria-hidden="true" />}
        {generate.isPending
          ? "Writing…"
          : hasVersions
            ? "Write another draft"
            : isLetter
              ? "Write my letter"
              : "Write my resume"}
      </Button>
    </section>
  );
}
