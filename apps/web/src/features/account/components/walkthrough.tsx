"use client";

import {
  ArrowRightIcon,
  CircleHelpIcon,
  FileTextIcon,
  HistoryIcon,
  MicIcon,
  SparklesIcon,
  StethoscopeIcon,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

import { useCurrentUser, useMarkTourSeen } from "../hooks";

type Step = {
  icon: typeof MicIcon;
  title: string;
  body: string;
  where: string;
  href: string;
};

/**
 * Five screens, in the order somebody actually uses them.
 *
 * Written for a first-timer who has never made a resume: it says what to do, not what the
 * product has. Nobody is made to read it — every step can be skipped.
 */
const STEPS: Step[] = [
  {
    icon: MicIcon,
    title: "Talk, and it writes your record",
    body: "You do not have to know what belongs on a resume. Answer in your own words — typed, or spoken into the microphone — and it keeps what you said: your name, your school, the job you did, the thing you built.",
    where: "Assistant",
    href: routes.assistant,
  },
  {
    icon: SparklesIcon,
    title: "It asks for your numbers",
    body: "“How many people used it?” “What was it like before?” Those answers are the difference between a resume that gets read and one that does not. They are yours — it asks for them, it never invents them.",
    where: "Assistant",
    href: routes.assistant,
  },
  {
    icon: FileTextIcon,
    title: "Write a resume in one click",
    body: "Press Create, pick a template, and say what it is for: a general resume, or one job in particular. Paste the advert and it leads with what that employer asked for. Cover letters work the same way.",
    where: "Resumes",
    href: routes.dashboard,
  },
  {
    icon: StethoscopeIcon,
    title: "It tells you what is weak",
    body: "“You have no projects.” “Nothing about this job has a number in it.” “Your grade is working against you” — with a button to leave it off. Against a job advert it also names the skills you are missing and two or three projects worth building.",
    where: "Profile",
    href: routes.profile,
  },
  {
    icon: HistoryIcon,
    title: "Nothing is thrown away",
    body: "Every resume and letter you write is kept and searchable, so applying for the same kind of role in June starts from the one you wrote in March. Download any of them as a PDF.",
    where: "History",
    href: routes.history,
  },
];

/**
 * The walkthrough: opens itself once for a new account, and stays reachable for everyone else.
 *
 * Having been shown it is remembered on the account, not in this browser, so it does not come
 * back on a second device — and the button is always there for somebody who wants a reminder.
 */
export function Walkthrough() {
  const account = useCurrentUser();
  const mark = useMarkTourSeen();
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  // Only ever offer it unasked once per page load, even if the account is refetched.
  const offered = useRef(false);

  const seen = account.data?.tour_seen;
  useEffect(() => {
    if (seen === false && !offered.current) {
      offered.current = true;
      setStep(0);
      setOpen(true);
    }
  }, [seen]);

  function close() {
    setOpen(false);
    // Closing counts as having been shown, however far they got. A failure here is not worth
    // interrupting anybody for; the worst case is being offered it once more.
    if (account.data && !account.data.tour_seen && !mark.isPending) mark.mutate();
  }

  const current = STEPS[step];
  const last = step === STEPS.length - 1;
  const Icon = current.icon;

  return (
    <>
      <Button
        variant="ghost"
        size="sm"
        className="text-muted-foreground"
        aria-label="How it works"
        onClick={() => {
          setStep(0);
          setOpen(true);
        }}
      >
        <CircleHelpIcon aria-hidden="true" />
        {/* The label is for the eye; the button is named for a screen reader either way. */}
        <span className="hidden sm:inline">How it works</span>
      </Button>

      <Dialog open={open} onOpenChange={(next) => (next ? setOpen(true) : close())}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <span className="flex size-10 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
              <Icon className="size-5" aria-hidden="true" />
            </span>
            <DialogTitle className="font-heading text-2xl">{current.title}</DialogTitle>
            <DialogDescription className="leading-relaxed">{current.body}</DialogDescription>
            <p className="text-xs text-muted-foreground">
              Where:{" "}
              <Link
                href={current.href}
                onClick={close}
                className="font-medium underline underline-offset-4"
              >
                {current.where}
              </Link>
            </p>
          </DialogHeader>

          <DialogFooter className="sm:items-center sm:justify-between">
            <div className="flex items-center gap-2" role="group" aria-label="Walkthrough steps">
              {STEPS.map((item, index) => (
                <button
                  key={item.title}
                  type="button"
                  aria-label={`Step ${index + 1}: ${item.title}`}
                  aria-current={index === step ? "step" : undefined}
                  onClick={() => setStep(index)}
                  className={cn(
                    "size-2 rounded-full transition-colors",
                    index === step ? "bg-foreground" : "bg-border hover:bg-muted-foreground",
                  )}
                />
              ))}
            </div>
            <div className="flex gap-2">
              {step > 0 ? (
                <Button variant="outline" onClick={() => setStep(step - 1)}>
                  Back
                </Button>
              ) : (
                <Button variant="ghost" onClick={close}>
                  Skip
                </Button>
              )}
              {last ? (
                <Link href={routes.assistant} onClick={close} className={buttonVariants()}>
                  Start talking
                  <ArrowRightIcon aria-hidden="true" />
                </Link>
              ) : (
                <Button onClick={() => setStep(step + 1)}>
                  Next
                  <ArrowRightIcon aria-hidden="true" />
                </Button>
              )}
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
