"use client";

import { LayoutTemplateIcon } from "lucide-react";
import Image from "next/image";
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
import type { ResumeTemplate } from "@/features/resumes/api";
import { useUpdateResume } from "@/features/resumes/hooks";
import { templateImage, templateInfo } from "@/features/resumes/templates";
import { errorMessage } from "@/lib/api/errors";

import { TemplateGallery } from "./template-gallery";

/**
 * The resume's template, and a way to change it. A template is only how the page looks, so the
 * change applies at once to every draft — nothing is rewritten, and no draft is lost.
 */
export function TemplateSetting({
  resumeId,
  template,
}: {
  resumeId: string;
  template: ResumeTemplate;
}) {
  const [open, setOpen] = useState(false);
  const [choice, setChoice] = useState<ResumeTemplate>(template);
  const update = useUpdateResume(resumeId);
  const info = templateInfo(template);

  async function onApply() {
    if (choice === template) {
      setOpen(false);
      return;
    }
    try {
      await update.mutateAsync({ template: choice });
      toast.success(`Now using ${templateInfo(choice).name}`);
      setOpen(false);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  return (
    <div className="flex items-center gap-4 rounded-lg border bg-background p-3">
      <span className="relative block h-20 w-14 shrink-0 overflow-hidden rounded border bg-white">
        <Image
          src={templateImage(template)}
          alt=""
          fill
          sizes="56px"
          className="object-cover object-top"
        />
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted-foreground">Template</p>
        <p className="font-medium">{info.name}</p>
        <p className="truncate text-xs text-muted-foreground">{info.bestFor}</p>
      </div>
      <Button
        variant="outline"
        onClick={() => {
          setChoice(template);
          setOpen(true);
        }}
      >
        <LayoutTemplateIcon aria-hidden="true" />
        Change
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[92dvh] overflow-y-auto sm:max-w-4xl">
          <DialogHeader>
            <DialogTitle className="font-heading text-2xl">Choose a template</DialogTitle>
            <DialogDescription>
              Only the look changes. Your drafts keep every word, and switch to the new template
              straight away.
            </DialogDescription>
          </DialogHeader>
          <TemplateGallery value={choice} onChange={setChoice} />
          <DialogFooter showCloseButton>
            <Button onClick={() => void onApply()} disabled={update.isPending}>
              {update.isPending ? <Spinner /> : null}
              Use {templateInfo(choice).name}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
