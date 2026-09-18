"use client";

import { ArrowLeftIcon, CheckIcon, MicIcon, SendIcon, SquareIcon } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { LoadFailure } from "@/components/feedback/load-failure";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import type { InterviewMessage, Turn } from "@/features/interview/api";
import {
  useAbandonInterview,
  useInterview,
  useSendAnswer,
  useStartInterview,
  useTranscribe,
} from "@/features/interview/hooks";
import { useRecorder } from "@/features/interview/use-recorder";
import { useResume } from "@/features/resumes/hooks";
import { errorMessage } from "@/lib/api/errors";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

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
        <Conversation interviewId={interviewId} resumeId={resumeId} />
      ) : (
        <InterviewSkeleton />
      )}
    </div>
  );
}

function Conversation({ interviewId, resumeId }: { interviewId: string; resumeId: string }) {
  const interview = useInterview(interviewId);
  const send = useSendAnswer(interviewId);
  const abandon = useAbandonInterview(interviewId);
  const transcribeAnswer = useTranscribe(interviewId);
  const recorder = useRecorder();
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<Record<string, Turn>>({});
  const endOfTranscript = useRef<HTMLDivElement>(null);

  const messages = interview.data?.messages ?? [];
  const status = interview.data?.session.status;
  const finished = status !== "active";

  useEffect(() => {
    endOfTranscript.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, send.isPending]);

  if (interview.isPending) return <InterviewSkeleton />;
  if (interview.isError) {
    return (
      <LoadFailure
        error={interview.error}
        onRetry={() => void interview.refetch()}
        retrying={interview.isRefetching}
        title="We couldn't load this interview"
      />
    );
  }

  async function onSend() {
    const text = draft.trim();
    if (!text || send.isPending) return;
    setDraft("");
    try {
      const turn = await send.mutateAsync(text);
      setTurns((current) => ({ ...current, [turn.reply.id]: turn }));
    } catch (error) {
      setDraft(text); // give them their words back rather than losing them
      toast.error(errorMessage(error));
    }
  }

  async function onRecord() {
    if (recorder.state === "recording") {
      const recording = await recorder.stop();
      if (!recording) return;
      try {
        const heard = await transcribeAnswer.mutateAsync(recording);
        // Into the box, not into the record: they read it back before it counts.
        setDraft((current) => (current ? `${current.trim()} ${heard}` : heard));
      } catch (error) {
        toast.error(errorMessage(error));
      }
      return;
    }
    try {
      await recorder.start();
    } catch {
      toast.error("We couldn't use your microphone. You can type your answer instead.");
    }
  }

  const busy = send.isPending || transcribeAnswer.isPending;

  return (
    <div className="space-y-4">
      <div className="space-y-4 rounded-xl border bg-card p-5 sm:p-6">
        <ol className="space-y-4">
          {messages.map((message) => (
            <li key={message.id}>
              <Bubble message={message} />
              <Recorded turn={turns[message.id]} />
            </li>
          ))}
        </ol>
        {send.isPending ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner />
            Writing that down…
          </p>
        ) : null}
        <div ref={endOfTranscript} />
      </div>

      {finished ? (
        <div className="flex flex-wrap gap-3">
          <Link href={routes.resume(resumeId)} className={buttonVariants()}>
            Back to the resume
          </Link>
          <Link href={routes.profile} className={buttonVariants({ variant: "outline" })}>
            Review my record
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          <Textarea
            aria-label="Your answer"
            value={draft}
            rows={3}
            placeholder={
              recorder.state === "recording" ? "Listening…" : "Type your answer, or speak it…"
            }
            disabled={busy}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              // Enter sends; Shift+Enter is a new line, as in every chat app.
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void onSend();
              }
            }}
          />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <Button
              variant="ghost"
              size="sm"
              disabled={abandon.isPending || recorder.state === "recording"}
              onClick={() => {
                abandon.mutate(undefined, {
                  onError: (error) => toast.error(errorMessage(error)),
                });
              }}
            >
              Stop here
            </Button>
            <div className="flex items-center gap-2">
              {recorder.state === "unsupported" ? null : (
                <Button
                  variant={recorder.state === "recording" ? "destructive" : "outline"}
                  onClick={() => void onRecord()}
                  disabled={busy || recorder.state === "stopping"}
                  aria-label={
                    recorder.state === "recording" ? "Stop recording" : "Answer by speaking"
                  }
                >
                  {transcribeAnswer.isPending ? (
                    <Spinner />
                  ) : recorder.state === "recording" ? (
                    <SquareIcon aria-hidden="true" />
                  ) : (
                    <MicIcon aria-hidden="true" />
                  )}
                  {transcribeAnswer.isPending
                    ? "Listening back…"
                    : recorder.state === "recording"
                      ? formatSeconds(recorder.seconds)
                      : "Speak"}
                </Button>
              )}
              <Button
                onClick={() => void onSend()}
                disabled={busy || !draft.trim() || recorder.state === "recording"}
              >
                {send.isPending ? <Spinner /> : <SendIcon aria-hidden="true" />}
                Send
              </Button>
            </div>
          </div>
          {recorder.state === "recording" ? (
            <p role="status" className="text-xs text-muted-foreground">
              Recording. Press stop when you&apos;re done, and check what we heard before sending.
            </p>
          ) : null}
        </div>
      )}
    </div>
  );
}

function Bubble({ message }: { message: InterviewMessage }) {
  const fromAgent = message.role === "agent";
  return (
    <div className={cn("flex", fromAgent ? "justify-start" : "justify-end")}>
      <p
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap",
          fromAgent ? "bg-muted" : "bg-primary text-primary-foreground",
        )}
      >
        <span className="sr-only">{fromAgent ? "Workaholic asked: " : "You answered: "}</span>
        {message.content}
      </p>
    </div>
  );
}

/** What the last answer put into the record, and what it refused to. */
function Recorded({ turn }: { turn: Turn | undefined }) {
  if (!turn || (turn.recorded.length === 0 && turn.dropped.length === 0)) return null;

  return (
    <div className="mt-2 space-y-1.5 pl-1">
      {turn.recorded.map((note) => (
        <p key={note} className="flex items-start gap-1.5 text-xs text-muted-foreground">
          <CheckIcon className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
          <span>
            <span className="sr-only">Recorded: </span>
            {note}
          </span>
        </p>
      ))}
      {turn.dropped.length > 0 ? (
        <p className="text-xs text-muted-foreground">
          Left out, because you didn&apos;t say it: {turn.dropped.join("; ")}
        </p>
      ) : null}
    </div>
  );
}

function formatSeconds(total: number): string {
  const minutes = Math.floor(total / 60);
  return `${minutes}:${String(total % 60).padStart(2, "0")}`;
}

function InterviewSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Starting the interview">
      <Skeleton className="h-12 w-72" />
      <Skeleton className="h-64 rounded-xl" />
      <Skeleton className="h-24 rounded-xl" />
    </div>
  );
}
