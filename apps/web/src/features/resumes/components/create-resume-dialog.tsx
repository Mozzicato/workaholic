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
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { ReadinessChecklist } from "@/features/profile/components/readiness-checklist";
import { useReadiness } from "@/features/profile/hooks";
import type { DocumentType } from "@/features/resumes/api";
import { useCreateResume } from "@/features/resumes/hooks";
import { templateInfo } from "@/features/resumes/templates";
import { errorMessage } from "@/lib/api/errors";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

import {
  BLANK,
  describes,
  PurposeChooser,
  useWriteDocument,
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
  const [letterTitle, setLetterTitle] = useState("");
  const router = useRouter();
  const readiness = useReadiness();
  const createResume = useCreateResume();
  const { write, step } = useWriteDocument();

  const isLetter = kind === "cover_letter";
  const checking = readiness.isPending;
  const ready = isLetter
    ? (readiness.data?.cover_letter_ready ?? false)
    : (readiness.data?.resume_ready ?? false);

  async function onSubmit() {
    try {
      if (isLetter) {
        // A letter needs the company and the advert, which the document's own page asks for.
        const letter = await createResume.mutateAsync({
          title: letterTitle.trim() || "Cover letter",
          document_type: "cover_letter",
        });
        setOpen(false);
        router.push(routes.resume(letter.id));
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
        if (step) return;
        setOpen(next);
        if (!next) setDocument(BLANK);
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
          <Field>
            <FieldLabel htmlFor="letter_title">Name it</FieldLabel>
            <Input
              id="letter_title"
              className="h-10"
              value={letterTitle}
              placeholder="Northwind letter"
              maxLength={120}
              onChange={(event) => setLetterTitle(event.target.value)}
            />
            <FieldDescription>
              The company and the advert are asked for on the next page.
            </FieldDescription>
          </Field>
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
            disabled={Boolean(step) || !ready || checking || (!isLetter && !describes(document))}
            onClick={() => void onSubmit()}
          >
            {step ? <Spinner /> : <SparklesIcon aria-hidden="true" />}
            {step ??
              (isLetter
                ? "Create letter"
                : document.purpose === "general"
                  ? `Write it in ${templateInfo(document.template).name}`
                  : "Write it for this job")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
