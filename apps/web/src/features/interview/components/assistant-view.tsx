"use client";

import { MessagesSquareIcon } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { useInterviews, useStartInterview } from "@/features/interview/hooks";
import { useSpeaker } from "@/features/interview/use-speaker";
import { ReadinessChecklist } from "@/features/profile/components/readiness-checklist";
import { useReadiness } from "@/features/profile/hooks";
import { CreateResumeDialog } from "@/features/resumes/components/create-resume-dialog";
import { errorMessage } from "@/lib/api/errors";
import { routes } from "@/lib/routes";

import { Conversation, ReadAloudToggle } from "./conversation";

/**
 * The guided way in: a conversation that walks someone through their resume from the top — name,
 * contact, school, grade, then what they've done — for people who would rather talk than fill in
 * forms. It writes only what they say, and it can take a CV part-way through.
 */
export function AssistantView() {
  const [interviewId, setInterviewId] = useState<string | null>(null);
  const start = useStartInterview();
  const interviews = useInterviews();
  const speaker = useSpeaker();

  // A conversation left unfinished is offered back, rather than silently replaced.
  const unfinished = interviews.data?.find(
    (session) => session.status === "active" && session.resume_id === null,
  );

  function onStart() {
    start.mutate(
      {},
      {
        onSuccess: (transcript) => setInterviewId(transcript.session.id),
        onError: (error) => toast.error(errorMessage(error)),
      },
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="font-heading text-4xl tracking-tight sm:text-5xl">
          Let&apos;s build your resume together
        </h1>
        <p className="max-w-prose leading-relaxed text-muted-foreground">
          I&apos;ll ask one thing at a time — your name, where you study, your grade, what
          you&apos;ve worked on — and write down only what you tell me. Talk or type, whichever is
          easier. Already have a CV? Upload it and I&apos;ll skip what it covers.
        </p>
      </header>

      {interviewId ? (
        <Conversation interviewId={interviewId} whenFinished={<Finished onAgain={onStart} />} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
          <section className="space-y-5 rounded-xl border bg-card p-5 sm:p-6">
            <div className="space-y-1">
              <h2 className="font-heading text-xl">Ready when you are</h2>
              <p className="text-sm leading-relaxed text-muted-foreground">
                It takes about five minutes. You can stop at any point — everything you&apos;ve said
                so far is kept.
              </p>
            </div>
            {speaker.supported ? <ReadAloudToggle speaker={speaker} /> : null}
            <div className="flex flex-wrap gap-3">
              <Button size="lg" onClick={onStart} disabled={start.isPending}>
                {start.isPending ? <Spinner /> : <MessagesSquareIcon aria-hidden="true" />}
                {unfinished ? "Start again" : "Start"}
              </Button>
              {unfinished ? (
                <Button
                  size="lg"
                  variant="outline"
                  disabled={start.isPending}
                  onClick={() => setInterviewId(unfinished.id)}
                >
                  Pick up where we left off
                </Button>
              ) : null}
            </div>
          </section>
          <WhatAResumeNeeds />
        </div>
      )}
    </div>
  );
}

function WhatAResumeNeeds() {
  const readiness = useReadiness();
  return (
    <section aria-labelledby="needs-heading" className="space-y-3">
      <h2 id="needs-heading" className="text-sm font-medium text-muted-foreground">
        What a resume needs
      </h2>
      <div className="rounded-xl border bg-card p-5">
        {readiness.data ? (
          <ReadinessChecklist readiness={readiness.data} />
        ) : readiness.isError ? (
          <p className="text-sm text-muted-foreground">
            Your name, a way to reach you, your education, something you&apos;ve done, and your
            skills.
          </p>
        ) : (
          <Skeleton className="h-32" />
        )}
      </div>
    </section>
  );
}

function Finished({ onAgain }: { onAgain: () => void }) {
  const readiness = useReadiness();
  if (!readiness.data) return <Skeleton className="h-40 rounded-xl" />;

  return (
    <section className="space-y-4 rounded-xl border bg-card p-5 sm:p-6">
      <h2 className="font-heading text-xl">
        {readiness.data.resume_ready ? "You're ready to write a resume" : "Nearly there"}
      </h2>
      <ReadinessChecklist readiness={readiness.data} />
      <div className="flex flex-wrap gap-3">
        {readiness.data.resume_ready ? (
          <CreateResumeDialog />
        ) : (
          <Button onClick={onAgain}>Keep going</Button>
        )}
        <Link href={routes.profile} className={buttonVariants({ variant: "outline" })}>
          Review my record
        </Link>
      </div>
    </section>
  );
}
