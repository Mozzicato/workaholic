"use client";

import { FileUpIcon } from "lucide-react";
import { useRef, useState } from "react";
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
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { useSendTemplateRequest } from "@/features/support/hooks";
import { errorMessage } from "@/lib/api/errors";

const ACCEPT =
  ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";

/**
 * "I already have a template I like." They send it in; a person looks at it and builds it.
 *
 * Deliberately not automatic. Copying an arbitrary design well enough to print someone's real
 * resume in it is not something to guess at, and a near-miss that claimed to be their template
 * would be worse than honestly saying a human does this.
 */
export function SendTemplateButton() {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [note, setNote] = useState("");
  const input = useRef<HTMLInputElement>(null);
  const send = useSendTemplateRequest();

  function close() {
    setOpen(false);
    setFile(null);
    setNote("");
  }

  async function onSend() {
    if (!file) return;
    try {
      await send.mutateAsync({ file, note });
      close();
      toast.success("Sent. We'll look at it and add it if we can.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  return (
    <>
      <Button type="button" variant="ghost" size="sm" onClick={() => setOpen(true)}>
        <FileUpIcon aria-hidden="true" />
        Have your own template?
      </Button>

      <Dialog
        open={open}
        onOpenChange={(next) => {
          if (!next) close();
          else setOpen(true);
        }}
      >
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-heading text-2xl">Send us your template</DialogTitle>
            <DialogDescription>
              Send the file and we will build it into Workaholic if we can. We do this by hand, so
              it is not instant — and we cannot promise every design.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <input
              ref={input}
              type="file"
              accept={ACCEPT}
              className="sr-only"
              aria-label="Choose a template file"
              onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            />
            <div className="flex flex-wrap items-center gap-3">
              <Button type="button" variant="outline" onClick={() => input.current?.click()}>
                <FileUpIcon aria-hidden="true" />
                Choose a file
              </Button>
              <span className="text-sm text-muted-foreground">
                {file ? file.name : "PDF or Word, up to 8 MB"}
              </span>
            </div>

            <Field>
              <FieldLabel htmlFor="template_note">Anything we should know? (optional)</FieldLabel>
              <Textarea
                id="template_note"
                rows={3}
                value={note}
                maxLength={2000}
                placeholder="Where it is from, or what you like about it."
                onChange={(event) => setNote(event.target.value)}
              />
              <FieldDescription>
                Your file is kept only until we have looked at it, then deleted. It is never read
                into your record, and never shown to anyone but the team.
              </FieldDescription>
            </Field>
          </div>

          <DialogFooter showCloseButton>
            <Button onClick={() => void onSend()} disabled={send.isPending || !file}>
              {send.isPending ? <Spinner /> : null}
              {send.isPending ? "Sending…" : "Send template"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
