"use client";

import { AlertTriangleIcon, CheckCircle2Icon, MessagesSquareIcon, XIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import type { AdviceItem } from "@/features/profile/api";
import { useAdvice, useProfile, useUpdateProfile } from "@/features/profile/hooks";
import { errorMessage } from "@/lib/api/errors";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

const CRITICAL = 1;
const IMPORTANT = 2;

/**
 * What would make this record produce a better resume, worst first.
 *
 * Advice, not a gate: everything here can be ignored. What it must never do is stay quiet while
 * somebody sends out a resume that a recruiter will put down in five seconds.
 */
export function RecordAdvice() {
  const advice = useAdvice();
  const router = useRouter();

  if (advice.isPending) return <Skeleton className="h-32 rounded-xl" />;
  if (advice.isError || !advice.data) return null;

  const { items, critical, important } = advice.data;
  if (items.length === 0) {
    return (
      <section className="rounded-xl border bg-card p-5">
        <p className="flex items-center gap-2 text-sm">
          <CheckCircle2Icon className="size-4 text-primary" aria-hidden="true" />
          Nothing here is holding your resume back. Anything you add from now on is a bonus.
        </p>
      </section>
    );
  }

  return (
    <section aria-labelledby="advice-heading" className="rounded-xl border bg-card">
      <div className="border-b px-5 py-4">
        <h2 id="advice-heading" className="font-heading text-xl">
          What would make this stronger
        </h2>
        <p className="mt-1 max-w-prose text-sm leading-relaxed text-muted-foreground">
          {critical > 0
            ? "Read the first one. A resume written from this would struggle, and it is not something better writing can fix."
            : important > 0
              ? "None of this stops you writing a resume. Each one is a real difference against somebody equally qualified."
              : "Small things, worth doing when you have a minute."}
        </p>
      </div>
      <ul className="divide-y">
        {items.map((item) => (
          <li key={item.key} className="px-5 py-4">
            <div className="flex items-start gap-3">
              {item.severity === CRITICAL ? (
                <AlertTriangleIcon
                  className="mt-0.5 size-4 shrink-0 text-destructive"
                  aria-hidden="true"
                />
              ) : null}
              <div className="min-w-0 flex-1">
                <p
                  className={cn(
                    "font-medium",
                    item.severity === CRITICAL && "text-destructive",
                    item.severity > IMPORTANT && "text-muted-foreground",
                  )}
                >
                  {item.title}
                </p>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{item.detail}</p>
                <p className="mt-1.5 text-sm leading-relaxed">{item.todo}</p>
              </div>
              <Fix item={item} onAssistant={() => router.push(routes.assistant)} />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** The one button that resolves this piece of advice, when there is one. */
function Fix({ item, onAssistant }: { item: AdviceItem; onAssistant: () => void }) {
  const profile = useProfile();
  const update = useUpdateProfile();

  if (item.action === "answer") {
    return (
      <Button variant="outline" size="sm" className="shrink-0" onClick={onAssistant}>
        <MessagesSquareIcon aria-hidden="true" />
        Answer
      </Button>
    );
  }

  if (item.action === "remove" && item.item_id) {
    return (
      <Button
        variant="outline"
        size="sm"
        className="shrink-0"
        disabled={update.isPending || !profile.data}
        onClick={() => {
          const education = (profile.data?.education ?? []).map((entry) =>
            entry.id === item.item_id ? { ...entry, grade: null } : entry,
          );
          update.mutate(
            { education },
            {
              onSuccess: () => toast.success("Left off. Your projects do the work instead."),
              onError: (error) => toast.error(errorMessage(error)),
            },
          );
        }}
      >
        {update.isPending ? <Spinner /> : <XIcon aria-hidden="true" />}
        Leave it off
      </Button>
    );
  }

  return null;
}
