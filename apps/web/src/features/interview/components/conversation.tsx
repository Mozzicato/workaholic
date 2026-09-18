"use client";

import {
  CheckIcon,
  FileUpIcon,
  MicIcon,
  SendIcon,
  SquareIcon,
  Volume2Icon,
  VolumeXIcon,
} from "lucide-react";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { LoadFailure } from "@/components/feedback/load-failure";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import type { InterviewMessage, Turn } from "@/features/interview/api";
import {
  useAbandonInterview,
  useContinueInterview,
  useInterview,
  useSendAnswer,
  useTranscribe,
} from "@/features/interview/hooks";
import { useRecorder } from "@/features/interview/use-recorder";
import { type Speaker, useSpeaker } from "@/features/interview/use-speaker";
import { DocumentImport } from "@/features/profile/components/import-section";
import { errorMessage } from "@/lib/api/errors";
import { cn } from "@/lib/utils";

/**
 * One conversation: questions, answers typed or spoken, and a CV upload part-way through.
 *
 * Questions are read aloud when the person wants that; a spoken answer lands in the box to be
 * checked before it is sent; an upload goes through the same review as on the profile page, and
 * the conversation then moves past whatever the document answered.
 */
export function Conversation({
  interviewId,
  whenFinished,
}: {
  interviewId: string;
  whenFinished: ReactNode;
}) {
  const interview = useInterview(interviewId);
  const send = useSendAnswer(interviewId);
  const carryOn = useContinueInterview(interviewId);
  const abandon = useAbandonInterview(interviewId);
  const transcribeAnswer = useTranscribe(interviewId);
  const recorder = useRecorder();
  const speaker = useSpeaker();
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<Record<string, Turn>>({});
  const [importing, setImporting] = useState(false);
  const endOfTranscript = useRef<HTMLDivElement>(null);

  const messages = interview.data?.messages ?? [];
  const status = interview.data?.session.status;
  const finished = status !== "active";
  const latestQuestion = [...messages].reverse().find((message) => message.role === "agent");

  useEffect(() => {
    endOfTranscript.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, send.isPending, importing]);

  // Each new question is read out once, as it arrives.
  const spoken = useRef<string | null>(null);
  const { enabled: readingAloud, speak } = speaker;
  useEffect(() => {
    if (!latestQuestion || spoken.current === latestQuestion.id) return;
    spoken.current = latestQuestion.id;
    if (readingAloud) speak(latestQuestion.content);
  }, [latestQuestion, readingAloud, speak]);

  if (interview.isPending) return <InterviewSkeleton />;
  if (interview.isError) {
    return (
      <LoadFailure
        error={interview.error}
        onRetry={() => void interview.refetch()}
        retrying={interview.isRefetching}
        title="We couldn't load this conversation"
      />
    );
  }

  async function onSend() {
    const text = draft.trim();
    if (!text || send.isPending) return;
    setDraft("");
    speaker.stop();
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
    // The microphone would otherwise hear the question being read out.
    speaker.stop();
    try {
      await recorder.start();
    } catch {
      toast.error("We couldn't use your microphone. You can type your answer instead.");
    }
  }

  function onImported() {
    setImporting(false);
    carryOn.mutate(undefined, {
      onSuccess: (turn) => setTurns((current) => ({ ...current, [turn.reply.id]: turn })),
      onError: (error) => toast.error(errorMessage(error)),
    });
  }

  const busy = send.isPending || transcribeAnswer.isPending || carryOn.isPending;

  return (
    <div className="space-y-4">
      {speaker.supported ? <ReadAloudToggle speaker={speaker} /> : null}

      <div className="space-y-4 rounded-xl border bg-card p-5 sm:p-6">
        <ol className="space-y-4">
          {messages.map((message) => (
            <li key={message.id}>
              <Bubble
                message={message}
                onReplay={
                  speaker.supported && message.id === latestQuestion?.id && !finished
                    ? () => speaker.speak(message.content)
                    : undefined
                }
              />
              <Recorded turn={turns[message.id]} />
            </li>
          ))}
        </ol>
        {send.isPending || carryOn.isPending ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner />
            {carryOn.isPending ? "Seeing what's still missing…" : "Writing that down…"}
          </p>
        ) : null}
        <div ref={endOfTranscript} />
      </div>

      {finished ? (
        whenFinished
      ) : importing ? (
        <div className="space-y-3 rounded-xl border border-dashed p-5">
          <p className="text-sm font-medium">Upload your CV</p>
          <p className="text-sm text-muted-foreground">
            You&apos;ll see what we read before anything is added. Then I&apos;ll only ask about
            what it didn&apos;t cover.
          </p>
          <DocumentImport onImported={onImported} onCancel={() => setImporting(false)} />
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
            <div className="flex flex-wrap items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                disabled={busy || recorder.state === "recording"}
                onClick={() => {
                  speaker.stop();
                  setImporting(true);
                }}
              >
                <FileUpIcon aria-hidden="true" />
                Upload a CV
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={abandon.isPending || recorder.state === "recording"}
                onClick={() => {
                  speaker.stop();
                  abandon.mutate(undefined, {
                    onError: (error) => toast.error(errorMessage(error)),
                  });
                }}
              >
                Stop here
              </Button>
            </div>
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

export function ReadAloudToggle({ speaker }: { speaker: Speaker }) {
  return (
    <Button
      variant="outline"
      size="sm"
      aria-pressed={speaker.enabled}
      onClick={() => speaker.setEnabled(!speaker.enabled)}
    >
      {speaker.enabled ? <Volume2Icon aria-hidden="true" /> : <VolumeXIcon aria-hidden="true" />}
      {speaker.enabled ? "Reading questions aloud" : "Read questions aloud"}
    </Button>
  );
}

function Bubble({ message, onReplay }: { message: InterviewMessage; onReplay?: () => void }) {
  const fromAgent = message.role === "agent";
  return (
    <div className={cn("flex items-end gap-1.5", fromAgent ? "justify-start" : "justify-end")}>
      <p
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap",
          fromAgent ? "bg-muted" : "bg-primary text-primary-foreground",
        )}
      >
        <span className="sr-only">{fromAgent ? "Workaholic asked: " : "You answered: "}</span>
        {message.content}
      </p>
      {onReplay ? (
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Hear the question again"
          onClick={onReplay}
        >
          <Volume2Icon aria-hidden="true" />
        </Button>
      ) : null}
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

export function InterviewSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Starting the conversation">
      <Skeleton className="h-12 w-72" />
      <Skeleton className="h-64 rounded-xl" />
      <Skeleton className="h-24 rounded-xl" />
    </div>
  );
}
