"use client";

import { MessageCircleIcon } from "lucide-react";
import { usePathname } from "next/navigation";
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
import { Field, FieldDescription, FieldLabel } from "@/components/ui/field";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { useSendFeedback } from "@/features/support/hooks";
import { errorMessage } from "@/lib/api/errors";

/**
 * A way to say something to the people who build this, from wherever you are.
 *
 * The page you were on is sent with the message, so a complaint about "this screen" can be
 * placed without asking which screen. Nothing else about the page goes with it.
 */
export function FeedbackButton() {
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const pathname = usePathname();
  const send = useSendFeedback();

  async function onSend() {
    const text = message.trim();
    if (!text) return;
    try {
      await send.mutateAsync({ message: text, page: pathname });
      setMessage("");
      setOpen(false);
      toast.success("Thank you — that reached the team.");
    } catch (error) {
      toast.error(errorMessage(error));
    }
  }

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(true)}
        className="fixed right-4 bottom-4 z-40 h-10 rounded-full bg-background px-4 shadow-lg"
      >
        <MessageCircleIcon aria-hidden="true" />
        Feedback
      </Button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-heading text-2xl">Tell us what you think</DialogTitle>
            <DialogDescription>
              Something broken, something missing, something that annoyed you — a person reads
              every one of these.
            </DialogDescription>
          </DialogHeader>

          <Field>
            <FieldLabel htmlFor="feedback">Your message</FieldLabel>
            <Textarea
              id="feedback"
              rows={5}
              value={message}
              maxLength={4000}
              placeholder="What happened, or what would you like to see?"
              onChange={(event) => setMessage(event.target.value)}
            />
            <FieldDescription>
              Sent with the page you are on ({pathname}) and your account email, so we can reply.
            </FieldDescription>
          </Field>

          <DialogFooter showCloseButton>
            <Button onClick={() => void onSend()} disabled={send.isPending || !message.trim()}>
              {send.isPending ? <Spinner /> : null}
              {send.isPending ? "Sending…" : "Send"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
