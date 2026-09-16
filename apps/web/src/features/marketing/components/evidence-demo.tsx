import { CheckIcon, XIcon } from "lucide-react";
import type { ReactNode } from "react";

/**
 * Illustrates the core pipeline with a clearly labelled example:
 * what the user said → evidence they confirm → the line Workaholic writes.
 */
export function EvidenceDemo() {
  return (
    <figure
      aria-label="Example: how an answer becomes a resume line"
      className="relative mx-auto w-full max-w-lg"
    >
      <div
        aria-hidden="true"
        className="absolute -inset-x-6 -inset-y-8 -z-10 rounded-[2.5rem] bg-accent/60 blur-2xl dark:bg-accent/30"
      />
      <div className="rounded-2xl border bg-card p-5 shadow-[0_1px_0_0_oklch(0_0_0/0.03),0_30px_60px_-30px_oklch(0.3_0.04_160/0.35)] sm:p-7">
        <div className="mb-6 flex items-center justify-between">
          <span className="font-mono text-[11px] tracking-[0.14em] text-muted-foreground uppercase">
            Example
          </span>
          <span className="flex gap-1" aria-hidden="true">
            <span className="size-2 rounded-full bg-border" />
            <span className="size-2 rounded-full bg-border" />
            <span className="size-2 rounded-full bg-border" />
          </span>
        </div>

        <ol className="space-y-6">
          <Step number="1" title="You said">
            <blockquote className="rounded-xl rounded-tl-sm bg-secondary px-4 py-3 text-[0.95rem] leading-relaxed">
              “I built a site at uni where students swap textbooks. Next.js front end, FastAPI back
              end. About 300 people signed up in the first semester.”
            </blockquote>
          </Step>

          <Step number="2" title="Evidence you confirm">
            <ul className="flex flex-wrap gap-2">
              <EvidenceChip label="Project" value="Textbook exchange" />
              <EvidenceChip label="Built with" value="Next.js, FastAPI" />
              <EvidenceChip label="Reach" value="~300 sign-ups" />
            </ul>
          </Step>

          <Step number="3" title="What goes on your resume">
            <p className="font-heading text-[1.35rem] leading-snug">
              Built a student textbook-exchange platform with{" "}
              <span className="evidence-mark">Next.js and FastAPI</span>, reaching{" "}
              <span className="evidence-mark">~300 sign-ups</span> in its first semester.
            </p>
            <div className="mt-4 flex items-start gap-2.5 rounded-lg border border-dashed border-destructive/35 bg-destructive/[0.04] px-3 py-2.5">
              <span className="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full bg-destructive/15 text-destructive">
                <XIcon className="size-3" aria-hidden="true" />
              </span>
              <p className="text-sm leading-snug text-muted-foreground">
                <s className="decoration-destructive/60">…cutting students&apos; book costs by 40%</s>
                <span className="mt-0.5 block text-xs">
                  You never said this, so Workaholic won&apos;t write it.
                </span>
              </p>
            </div>
          </Step>
        </ol>
      </div>
    </figure>
  );
}

function Step({ number, title, children }: { number: string; title: string; children: ReactNode }) {
  return (
    <li className="relative grid grid-cols-[1.75rem_minmax(0,1fr)] gap-x-3">
      <span
        aria-hidden="true"
        className="flex size-7 items-center justify-center rounded-full border bg-background font-mono text-xs text-muted-foreground"
      >
        {number}
      </span>
      <div className="min-w-0 space-y-2.5">
        <p className="pt-1 text-xs font-medium tracking-wide text-muted-foreground uppercase">{title}</p>
        {children}
      </div>
    </li>
  );
}

function EvidenceChip({ label, value }: { label: string; value: string }) {
  return (
    <li className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-accent/70 py-1 pr-3 pl-1.5 text-sm">
      <span className="flex size-5 items-center justify-center rounded-full bg-primary text-primary-foreground">
        <CheckIcon className="size-3" aria-hidden="true" />
      </span>
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-accent-foreground">{value}</span>
    </li>
  );
}
