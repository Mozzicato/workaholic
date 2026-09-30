"use client";

import { PlusIcon, SparklesIcon } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { ReadinessChecklist } from "@/features/profile/components/readiness-checklist";
import { useReadiness } from "@/features/profile/hooks";
import type { DocumentType } from "@/features/resumes/api";
import { templateInfo } from "@/features/resumes/templates";
import { errorMessage } from "@/lib/api/errors";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

import {
  BLANK,
  describes,
  LetterFields,
  NO_LETTER,
  PurposeChooser,
  useWriteDocument,
  useWriteLetter,
  type LetterDetails,
  type NewDocument,
} from "./new-document";
import { TemplateGallery } from "./template-gallery";

const KINDS = [
  { value: "resume", label: "Resume", description: "Your experience, on one page" },
  { value: "cover_letter", label: "Cover letter", description: "A letter for one application" },
] as const satisfies readonly { value: DocumentType; label: string; description: string }[];

/**
 * Start something new: what kind, what it is for, and how it should look — then it is written.
 *
 * The same three questions as starting from the record, because it is the same act.
 */
export function CreateResumeDialog({ variant = "default" }: { variant?: "default" | "outline" }) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<DocumentType>("resume");
  const [document, setDocument] = useState<NewDocument>(BLANK);
  const [letter, setLetter] = useState<LetterDetails>(NO_LETTER);
  const router = useRouter();
  const readiness = useReadiness();
  const { write, step } = useWriteDocument();
  const letters = useWriteLetter();
  const busy = step ?? letters.step;

  const isLetter = kind === "cover_letter";
  const checking = readiness.isPending;
  const ready = isLetter
    ? (readiness.data?.cover_letter_ready ?? false)
    : (readiness.data?.resume_ready ?? false);

  async function onSubmit() {
    try {
      if (isLetter) {
        const written = await letters.write(letter);
        setOpen(false);
        router.push(routes.resume(written));
        return;
      }
      const resumeId = await write(document);
      setOpen(false);
      router.push(routes.resume(resumeId));
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (busy) return;
        setOpen(next);
        if (!next) {
          setDocument(BLANK);
          setLetter(NO_LETTER);
        }
      }}
    >
      <DialogTrigger
        render={
          <Button size="lg" variant={variant} className="h-10">
            <PlusIcon aria-hidden="true" />
            Create
          </Button>
        }
      />
      <DialogContent className="max-h-[92dvh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle className="font-heading text-2xl">Start something new</DialogTitle>
          <DialogDescription>
            Written from your record. Nothing is added that you have not told us.
          </DialogDescription>
        </DialogHeader>

        <fieldset>
          <legend className="text-sm font-medium">What are you making?</legend>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {KINDS.map((option) => (
              <button
                key={option.value}
                type="button"
                aria-pressed={kind === option.value}
                onClick={() => setKind(option.value)}
                className={cn(
                  "rounded-lg border px-3 py-2.5 text-left transition-colors outline-none",
                  "focus-visible:ring-3 focus-visible:ring-ring/50",
                  kind === option.value ? "border-primary bg-accent" : "hover:bg-muted/60",
                )}
              >
                <span className="block text-sm font-medium">{option.label}</span>
                <span className="block text-xs text-muted-foreground">{option.description}</span>
              </button>
            ))}
          </div>
        </fieldset>

        {!checking && !ready && readiness.data ? (
          <div className="rounded-lg border border-dashed p-4">
            <p className="text-sm font-medium">
              Your record needs a little more before this can be written:
            </p>
            <ReadinessChecklist readiness={readiness.data} letter={isLetter} className="mt-3" />
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={() => {
                setOpen(false);
                router.push(routes.assistant);
              }}
            >
              Answer a few questions
            </Button>
          </div>
        ) : null}

        {isLetter ? (
          <LetterFields value={letter} onChange={setLetter} />
        ) : (
          <>
            <PurposeChooser value={document} onChange={setDocument} />
            <TemplateGallery
              value={document.template}
              onChange={(template) => setDocument({ ...document, template })}
            />
          </>
        )}

        <DialogFooter showCloseButton>
          <Button
            size="lg"
            className="h-10"
            disabled={
              Boolean(busy) ||
              !ready ||
              checking ||
              (isLetter ? !letter.company.trim() : !describes(document))
            }
            onClick={() => void onSubmit()}
          >
            {busy ? <Spinner /> : <SparklesIcon aria-hidden="true" />}
            {busy ??
              (isLetter
                ? "Write my letter"
                : document.purpose === "general"
                  ? `Write it in ${templateInfo(document.template).name}`
                  : "Write it for this job")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
