"use client";

import { ArrowLeftIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { LoadFailure } from "@/components/feedback/load-failure";
import { buttonVariants } from "@/components/ui/button";
import { useStartInterview } from "@/features/interview/hooks";
import { useResume } from "@/features/resumes/hooks";
import { errorMessage } from "@/lib/api/errors";
import { routes } from "@/lib/routes";

import { Conversation, InterviewSkeleton } from "./conversation";

export function InterviewView({ resumeId }: { resumeId: string }) {
  const [interviewId, setInterviewId] = useState<string | null>(null);
  const resume = useResume(resumeId);
  const start = useStartInterview();

  // One interview per visit: started on arrival, continued until it finishes or you leave.
  const started = useRef(false);
  useEffect(() => {
    if (started.current || !resume.data) return;
    started.current = true;
    start.mutate(
      { resume_id: resumeId, target_role: resume.data.target_role },
      {
        onSuccess: (transcript) => setInterviewId(transcript.session.id),
        onError: (error) => toast.error(errorMessage(error)),
      },
    );
  }, [resume.data, resumeId, start]);

  if (resume.isPending || (!interviewId && start.isPending)) return <InterviewSkeleton />;

  if (resume.isError || start.isError) {
    return (
      <LoadFailure
        error={resume.error ?? start.error}
        onRetry={() => window.location.reload()}
        retrying={false}
        title="We couldn't start the interview"
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link
          href={routes.resume(resumeId)}
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeftIcon className="size-4" aria-hidden="true" />
          Back to {resume.data?.title ?? "the resume"}
        </Link>
      </div>

      <header className="space-y-2">
        <h1 className="font-heading text-4xl tracking-tight sm:text-5xl">Tell me what you did</h1>
        <p className="max-w-prose leading-relaxed text-muted-foreground">
          Answer in your own words — rough is fine. Everything you say goes into your career record,
          and nothing else does.
        </p>
      </header>

      {interviewId ? (
        <Conversation
          interviewId={interviewId}
          whenFinished={
            <div className="flex flex-wrap gap-3">
              <Link href={routes.resume(resumeId)} className={buttonVariants()}>
                Back to the resume
              </Link>
              <Link href={routes.profile} className={buttonVariants({ variant: "outline" })}>
                Review my record
              </Link>
            </div>
          }
        />
      ) : (
        <InterviewSkeleton />
      )}
    </div>
  );
}
