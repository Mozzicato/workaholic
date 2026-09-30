"use client";

import { HammerIcon, LightbulbIcon } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { useCoaching } from "@/features/jobs/hooks";

/**
 * What this job asks for that the record cannot support, and what to do about it.
 *
 * The obvious move here is to quietly add the keyword. We do the useful thing instead: say what
 * they have already done that is close, and give them something small to build that would make
 * the claim real. Nothing on this panel reaches a resume.
 */
export function GapCoaching({ jobId }: { jobId: string }) {
  const coaching = useCoaching(jobId);

  if (coaching.isPending) return <Skeleton className="h-40 rounded-xl" />;
  if (coaching.isError || !coaching.data) return null;

  const { gaps, ideas, caveat } = coaching.data;
  if (gaps.length === 0) {
    return (
      <section className="rounded-xl border bg-card p-5">
        <h2 className="font-heading text-xl">Nothing here you cannot back up</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Everything this job asks for is something your record supports. Apply.
        </p>
      </section>
    );
  }

  const withAdjacent = gaps.filter((gap) => gap.adjacent.length > 0);

  return (
    <section aria-labelledby="coaching-heading" className="space-y-4 rounded-xl border bg-card p-5">
      <div>
        <h2 id="coaching-heading" className="font-heading text-xl">
          What they want that you do not have yet
        </h2>
        <p className="mt-1 max-w-prose text-sm leading-relaxed text-muted-foreground">{caveat}</p>
      </div>

      <ul className="flex flex-wrap gap-2">
        {gaps.map((gap) => (
          <li
            key={gap.skill}
            className="rounded-full border border-dashed px-3 py-1 text-sm text-muted-foreground"
          >
            {gap.skill}
          </li>
        ))}
      </ul>

      {withAdjacent.length > 0 ? (
        <div className="rounded-lg bg-muted/60 p-4">
          <p className="flex items-center gap-2 text-sm font-medium">
            <LightbulbIcon className="size-4" aria-hidden="true" />
            Say this in the interview
          </p>
          <ul className="mt-2 space-y-1.5 text-sm leading-relaxed">
            {withAdjacent.map((gap) => (
              <li key={gap.skill}>
                You have not used <span className="font-medium">{gap.skill}</span>, but you have
                used <span className="font-medium">{gap.adjacent.join(", ")}</span>. Say so plainly
                — it is the nearest true thing, and it is worth more than silence.
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {ideas.length > 0 ? (
        <div className="space-y-3">
          <p className="flex items-center gap-2 text-sm font-medium">
            <HammerIcon className="size-4" aria-hidden="true" />
            Build one of these, and it stops being a gap
          </p>
          {ideas.map((idea) => (
            <article key={idea.title} className="rounded-lg border p-4">
              <h3 className="font-medium">{idea.title}</h3>
              {idea.covers.length > 0 ? (
                <p className="mt-0.5 text-xs text-muted-foreground">
                  Earns: {idea.covers.join(", ")}
                </p>
              ) : null}
              <p className="mt-1.5 text-sm leading-relaxed">{idea.summary}</p>
              <ol className="mt-2 list-decimal space-y-1 pl-5 text-sm leading-relaxed text-muted-foreground">
                {idea.steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            </article>
          ))}
          <p className="text-xs text-muted-foreground">
            When one of these is finished, add it as a project with its repository link. It goes on
            your resume then, and you will be able to answer questions about it.
          </p>
        </div>
      ) : null}
    </section>
  );
}
