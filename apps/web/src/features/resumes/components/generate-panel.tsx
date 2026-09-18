"use client";

import { SparklesIcon } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import type { ResumeTemplate } from "@/features/resumes/api";
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
  hasVersions,
  onGenerated,
}: {
  resumeId: string;
  hasVersions: boolean;
  onGenerated: (versionId: string) => void;
}) {
  const [template, setTemplate] = useState<ResumeTemplate>("standard");
  const [blocked, setBlocked] = useState<{
    title: string;
    message: string;
    problems: string[];
  } | null>(null);
  const generate = useGenerateVersion(resumeId);

  async function onGenerate() {
    setBlocked(null);
    try {
      const version = await generate.mutateAsync(template);
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
        {hasVersions ? "Write another draft" : "Write this resume"}
      </h2>
      <p className="mt-1 max-w-prose text-sm leading-relaxed text-muted-foreground">
        Workaholic rewrites what you recorded so it reads well. It never adds a number, a tool or an
        employer you didn&apos;t mention — if the wording would go beyond your record, the draft is
        refused instead.
      </p>

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

      <Button className="mt-5" onClick={() => void onGenerate()} disabled={generate.isPending}>
        {generate.isPending ? <Spinner /> : <SparklesIcon aria-hidden="true" />}
        {generate.isPending ? "Writing…" : hasVersions ? "Write another draft" : "Write my resume"}
      </Button>
    </section>
  );
}
