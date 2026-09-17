import type { ReactNode } from "react";

/** One editable area of the career record: a heading, an explanation, and its contents. */
export function SectionCard({
  id,
  title,
  description,
  action,
  children,
}: {
  id: string;
  title: string;
  description: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section aria-labelledby={`${id}-heading`} className="rounded-xl border bg-card">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b px-5 py-4 sm:px-6">
        <div className="space-y-1">
          <h2 id={`${id}-heading`} className="font-heading text-xl">
            {title}
          </h2>
          <p className="max-w-prose text-sm leading-relaxed text-muted-foreground">{description}</p>
        </div>
        {action}
      </div>
      <div className="px-5 py-5 sm:px-6">{children}</div>
    </section>
  );
}

export function EmptySectionNote({ children }: { children: ReactNode }) {
  return <p className="text-sm text-muted-foreground">{children}</p>;
}
