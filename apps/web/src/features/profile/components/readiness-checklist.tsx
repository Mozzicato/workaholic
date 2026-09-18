"use client";

import { CheckCircle2Icon, CircleIcon } from "lucide-react";

import type { Readiness } from "@/features/profile/api";
import { cn } from "@/lib/utils";

/** What a cover letter needs. Education and skills belong on a resume, not in a letter. */
const LETTER_KEYS = new Set(["name", "contact", "experience_or_projects"]);

export function checklistFor(readiness: Readiness, letter: boolean) {
  return letter ? readiness.items.filter((item) => LETTER_KEYS.has(item.key)) : readiness.items;
}

export function isReady(readiness: Readiness, letter: boolean): boolean {
  return letter ? readiness.cover_letter_ready : readiness.resume_ready;
}

/**
 * What the record holds, and what it still needs, before anything is written from it.
 *
 * Shown before writing rather than after: an ATS check pointing out a missing education section
 * is too late if the resume has already been sent.
 */
export function ReadinessChecklist({
  readiness,
  letter = false,
  className,
}: {
  readiness: Readiness;
  letter?: boolean;
  className?: string;
}) {
  const items = checklistFor(readiness, letter);
  return (
    <ul className={cn("space-y-2.5", className)} aria-label="What your record needs">
      {items.map((item) => (
        <li key={item.key} className="flex items-start gap-2.5 text-sm">
          {item.done ? (
            <CheckCircle2Icon className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
          ) : (
            <CircleIcon
              className="mt-0.5 size-4 shrink-0 text-muted-foreground"
              aria-hidden="true"
            />
          )}
          <span>
            <span className={cn("font-medium", item.done && "text-muted-foreground")}>
              {item.label}
            </span>
            <span className="sr-only">{item.done ? ": done" : ": still needed"}</span>
            {item.done ? null : (
              <span className="block text-xs text-muted-foreground">{item.hint}</span>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}
