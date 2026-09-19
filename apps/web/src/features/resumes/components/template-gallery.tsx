"use client";

import { CheckIcon, Columns2Icon } from "lucide-react";
import Image from "next/image";

import type { ResumeTemplate } from "@/features/resumes/api";
import { TEMPLATES, templateImage } from "@/features/resumes/templates";
import { cn } from "@/lib/utils";

/**
 * Every template as a picture of the page it prints. One choice at a time, like radio buttons:
 * arrow keys move between cards, and the chosen one is announced as selected.
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
  return (
    <div className={className}>
      <div
        role="radiogroup"
        aria-label="Resume templates"
        className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4"
        onKeyDown={(event) => {
          const keys = ["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp"];
          if (!keys.includes(event.key)) return;
          event.preventDefault();
          const step = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : -1;
          const index = TEMPLATES.findIndex((template) => template.key === value);
          const next = TEMPLATES[(index + step + TEMPLATES.length) % TEMPLATES.length];
          onChange(next.key);
          const card = event.currentTarget.querySelector<HTMLElement>(
            `[data-template="${next.key}"]`,
          );
          card?.focus();
        }}
      >
        {TEMPLATES.map((template) => {
          const selected = template.key === value;
          return (
            <button
              key={template.key}
              type="button"
              role="radio"
              aria-checked={selected}
              data-template={template.key}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(template.key)}
              className={cn(
                "group relative flex flex-col overflow-hidden rounded-lg border bg-card text-left transition outline-none",
                "focus-visible:ring-3 focus-visible:ring-ring/50",
                selected ? "border-primary ring-2 ring-primary" : "hover:border-foreground/30",
              )}
            >
              <span className="relative block aspect-[210/297] w-full overflow-hidden border-b bg-white">
                <Image
                  src={templateImage(template.key)}
                  alt=""
                  fill
                  sizes="(min-width: 1024px) 200px, (min-width: 640px) 30vw, 45vw"
                  className="object-cover object-top transition-transform duration-300 group-hover:scale-[1.02]"
                />
                {selected ? (
                  <span className="absolute top-2 right-2 grid size-6 place-items-center rounded-full bg-primary text-primary-foreground shadow">
                    <CheckIcon className="size-3.5" aria-hidden="true" />
                  </span>
                ) : null}
              </span>
              <span className="flex flex-1 flex-col gap-1 p-2.5">
                <span className="flex items-center gap-1.5 text-sm font-medium">
                  {template.name}
                  {template.twoColumns ? (
                    <Columns2Icon className="size-3.5 text-muted-foreground" aria-hidden="true" />
                  ) : null}
                </span>
                <span className="text-xs leading-snug text-muted-foreground">
                  {template.bestFor}
                </span>
              </span>
            </button>
          );
        })}
      </div>
      <TemplateNote value={value} />
    </div>
  );
}

/** What the chosen template is, in a sentence, and the one honest warning some deserve. */
function TemplateNote({ value }: { value: ResumeTemplate }) {
  const template = TEMPLATES.find((item) => item.key === value);
  if (!template) return null;
  return (
    <div className="mt-3 space-y-1 rounded-lg bg-muted/60 px-3 py-2.5 text-sm" aria-live="polite">
      <p>
        <span className="font-medium">{template.name}:</span> {template.description}{" "}
        <span className="text-muted-foreground">{template.traits.join(" · ")}.</span>
      </p>
      {template.twoColumns ? (
        <p className="text-xs text-muted-foreground">
          Two columns look good to people, but some older applicant-tracking systems read them out
          of order. For online applications, a one-column template is the safer choice.
        </p>
      ) : null}
      <p className="text-xs text-muted-foreground">
        The pictures show an example person. Your resume uses only your own record.
      </p>
    </div>
  );
}
