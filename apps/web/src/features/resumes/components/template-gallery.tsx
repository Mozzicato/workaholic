"use client";

import { ChevronLeftIcon, ChevronRightIcon, Columns2Icon } from "lucide-react";
import Image from "next/image";
import { useEffect, useRef } from "react";

import { Button } from "@/components/ui/button";
import { SendTemplateButton } from "@/features/support/components/send-template";
import type { ResumeTemplate } from "@/features/resumes/api";
import { TEMPLATES, templateImage } from "@/features/resumes/templates";
import { cn } from "@/lib/utils";

/**
 * One template at a time, big enough to read, with the rest as a strip underneath.
 *
 * A thumbnail small enough to fit eleven on a screen is too small to judge a resume by, which is
 * the whole point of choosing one — so the page you would print is shown full width, and the
 * strip is only for moving between them.
 */
export function TemplateGallery({
  value,
  onChange,
  className,
}: {
  value: ResumeTemplate;
  onChange: (template: ResumeTemplate) => void;
  className?: string;
}) {
  const index = Math.max(
    0,
    TEMPLATES.findIndex((template) => template.key === value),
  );
  const current = TEMPLATES[index];
  const strip = useRef<HTMLDivElement>(null);

  function step(by: number) {
    onChange(TEMPLATES[(index + by + TEMPLATES.length) % TEMPLATES.length].key);
  }

  // Keep the chosen thumbnail in view when the arrows move past the edge of the strip.
  useEffect(() => {
    const chosen = strip.current?.querySelector<HTMLElement>('[aria-checked="true"]');
    // Optional: not every environment implements scrolling (jsdom, older browsers).
    chosen?.scrollIntoView?.({ behavior: "smooth", block: "nearest", inline: "center" });
  }, [value]);

  return (
    <div
      className={cn("space-y-3", className)}
      onKeyDown={(event) => {
        if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") return;
        event.preventDefault();
        step(event.key === "ArrowRight" ? 1 : -1);
      }}
    >
      <div className="relative">
        <div className="relative mx-auto aspect-[210/297] w-full max-w-[420px] overflow-hidden rounded-lg border bg-white shadow-sm">
          <Image
            key={current.key}
            src={templateImage(current.key)}
            alt={`The ${current.name} template, filled in with an example person's details`}
            fill
            priority
            sizes="(min-width: 640px) 420px, 90vw"
            className="object-contain"
          />
        </div>

        <Button
          type="button"
          variant="outline"
          size="icon"
          aria-label="Previous template"
          onClick={() => step(-1)}
          className="absolute top-1/2 left-0 -translate-y-1/2 rounded-full shadow-sm sm:-left-3"
        >
          <ChevronLeftIcon aria-hidden="true" />
        </Button>
        <Button
          type="button"
          variant="outline"
          size="icon"
          aria-label="Next template"
          onClick={() => step(1)}
          className="absolute top-1/2 right-0 -translate-y-1/2 rounded-full shadow-sm sm:-right-3"
        >
          <ChevronRightIcon aria-hidden="true" />
        </Button>
      </div>

      <div aria-live="polite" className="space-y-1 text-center">
        <p className="flex items-center justify-center gap-1.5 font-heading text-lg">
          {current.name}
          {current.twoColumns ? (
            <Columns2Icon className="size-4 text-muted-foreground" aria-hidden="true" />
          ) : null}
          <span className="text-sm text-muted-foreground">
            ({index + 1} of {TEMPLATES.length})
          </span>
        </p>
        <p className="mx-auto max-w-prose text-sm text-muted-foreground">
          {current.description} Best for {current.bestFor.toLowerCase()}.
        </p>
        {current.twoColumns ? (
          <p className="mx-auto max-w-prose text-xs text-muted-foreground">
            Two columns look good to people, but some older applicant-tracking systems read them out
            of order. For online applications, a one-column template is the safer choice.
          </p>
        ) : null}
      </div>

      <div
        ref={strip}
        role="radiogroup"
        aria-label="Resume templates"
        className="flex gap-2 overflow-x-auto pb-1"
      >
        {TEMPLATES.map((template) => {
          const selected = template.key === value;
          return (
            <button
              key={template.key}
              type="button"
              role="radio"
              aria-checked={selected}
              aria-label={template.name}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(template.key)}
              className={cn(
                "relative aspect-[210/297] w-16 shrink-0 overflow-hidden rounded border bg-white transition outline-none",
                "focus-visible:ring-3 focus-visible:ring-ring/50",
                selected ? "border-primary ring-2 ring-primary" : "opacity-70 hover:opacity-100",
              )}
            >
              <Image
                src={templateImage(template.key)}
                alt=""
                fill
                sizes="64px"
                className="object-cover object-top"
              />
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1">
        <p className="text-xs text-muted-foreground">
          The pictures show an example person. Your resume uses only your own record.
        </p>
        <SendTemplateButton />
      </div>
    </div>
  );
}
