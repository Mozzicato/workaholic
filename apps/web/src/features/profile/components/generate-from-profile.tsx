"use client";

import { SparklesIcon } from "lucide-react";
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
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { ReadinessChecklist } from "@/features/profile/components/readiness-checklist";
import { useReadiness } from "@/features/profile/hooks";
import {
  BLANK,
  describes,
  PurposeChooser,
  useWriteDocument,
  type NewDocument,
} from "@/features/resumes/components/new-document";
import { TemplateGallery } from "@/features/resumes/components/template-gallery";
import { errorMessage } from "@/lib/api/errors";
import { routes } from "@/lib/routes";

/**
 * Write the resume from here, where the record is.
 *
 * Somebody filling in their details should not have to find another page to get the thing they
 * came for. The questions are the same ones the Create button asks, because it is the same act.
 */
export function GenerateFromProfile() {
  const readiness = useReadiness();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [document, setDocument] = useState<NewDocument>(BLANK);
  const { write, step } = useWriteDocument();

  // Until the check comes back, say nothing about the record: telling somebody their record is
  // short and then correcting yourself half a second later is worse than waiting.
  const checking = readiness.isPending;
  const ready = readiness.data?.resume_ready ?? false;

  async function onGenerate() {
    try {
      const resumeId = await write(document);
      setOpen(false);
      router.push(routes.resume(resumeId));
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  return (
    <section
      aria-labelledby="generate-heading"
      className="rounded-xl border border-primary/30 bg-accent/30 p-5 sm:p-6"
    >
      <h2 id="generate-heading" className="font-heading text-xl">
        {checking ? "Your resume" : ready ? "Ready to write your resume" : "Not quite ready yet"}
      </h2>
      <p className="mt-1 max-w-prose text-sm leading-relaxed text-muted-foreground">
        {checking
          ? "Checking what your record holds…"
          : ready
            ? "Everything on this page is what a resume can say. Write one that covers all of it, or one aimed at a job you are applying for."
            : "A resume written from this would be missing things employers look for first. Here is what it still needs."}
      </p>

      {readiness.data && !ready && !checking ? (
        <ReadinessChecklist readiness={readiness.data} className="mt-4" />
      ) : null}

      <div className="mt-5 flex flex-wrap gap-3">
        <Button
          size="lg"
          className="h-10"
          disabled={!ready || checking}
          onClick={() => setOpen(true)}
        >
          <SparklesIcon aria-hidden="true" />
          Generate my resume
        </Button>
        {!ready && !checking ? (
          <Button
            size="lg"
            variant="outline"
            className="h-10"
            onClick={() => router.push(routes.assistant)}
          >
            Answer a few questions instead
          </Button>
        ) : null}
      </div>

      <Dialog open={open} onOpenChange={(next) => (step ? null : setOpen(next))}>
        <DialogContent className="max-h-[92dvh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle className="font-heading text-2xl">Write my resume</DialogTitle>
            <DialogDescription>
              Written from your record. Nothing is added that you have not told us.
            </DialogDescription>
          </DialogHeader>

          <PurposeChooser value={document} onChange={setDocument} />
          <TemplateGallery
            value={document.template}
            onChange={(template) => setDocument({ ...document, template })}
          />

          <DialogFooter showCloseButton>
            <Button
              size="lg"
              className="h-10"
              disabled={Boolean(step) || !describes(document)}
              onClick={() => void onGenerate()}
            >
              {step ? <Spinner /> : <SparklesIcon aria-hidden="true" />}
              {step ?? "Write it"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  );
}
