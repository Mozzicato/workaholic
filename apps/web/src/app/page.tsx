import { ArrowRightIcon, CheckIcon, MinusIcon } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { Logo } from "@/components/brand/logo";
import { WarmApi } from "@/components/system/warm-api";
import { buttonVariants } from "@/components/ui/button";
import { EvidenceDemo } from "@/features/marketing/components/evidence-demo";
import { routes } from "@/lib/routes";
import { cn } from "@/lib/utils";

const STEPS = [
  {
    title: "Talk it through",
    body: "Answer focused questions by typing or speaking. Workaholic follows up with things like “Did anyone actually use it?” — not “tell me more.”",
  },
  {
    title: "Confirm the evidence",
    body: "Every fact it picks up is shown back to you. Only what you said or confirmed can become a claim on your resume.",
  },
  {
    title: "Get a clean resume",
    body: "A structured, single-column document with real, selectable text that applicant tracking systems can read.",
  },
  {
    title: "Tailor it to a real job",
    body: "Paste a job description to see what matches, what's missing, and exactly what changed in the tailored version.",
  },
];

const WILL = [
  "Tighten grammar, clarity and structure",
  "Lead with outcomes and what's relevant to the role",
  "Point out where a number would make a line stronger — and ask you for it",
  "Explain every change it makes when tailoring",
];

const WONT = [
  "Invent metrics, users or results",
  "Add employers, dates or certifications",
  "Claim skills or tools you never mentioned",
  "Silently rewrite something you approved",
];

const ATS_CHECKS = [
  "Text can be extracted",
  "Recognisable section headings",
  "Contact details present",
  "Consistent dates",
  "Keyword coverage for the job",
  "Readable formatting",
  "Sensible length",
];

export default function HomePage() {
  return (
    <div className="flex min-h-dvh flex-col">
      {/* Most people meet the product here and click through to sign up. Start the API now,
          so the wait happens while they read rather than after they press a button. */}
      <WarmApi />
      <SiteHeader />

      <main className="flex-1">
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div className="mx-auto grid max-w-6xl items-center gap-14 px-4 pt-12 pb-20 sm:px-6 sm:pt-20 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] lg:gap-10 lg:pt-24 lg:pb-28">
            <div>
              <p className="inline-flex items-center gap-2 rounded-full border bg-card px-3 py-1 text-xs text-muted-foreground">
                <span className="size-1.5 rounded-full bg-primary" aria-hidden="true" />
                Evidence-first resume builder
              </p>
              <h1 className="mt-6 font-heading text-[3.25rem] leading-[0.98] tracking-tight sm:text-7xl lg:text-[5.25rem]">
                Your real experience, <em className="text-primary">written&nbsp;well.</em>
              </h1>
              <p className="mt-6 max-w-xl text-lg leading-relaxed text-muted-foreground">
                Workaholic interviews you about what you&apos;ve actually done, turns your answers
                into evidence you confirm, and writes a clean, ATS-readable resume from it. It never
                invents a metric, an employer or a skill.
              </p>
              <div className="mt-9 flex flex-wrap items-center gap-3">
                <Link
                  href={routes.signup}
                  className={cn(buttonVariants({ size: "lg" }), "h-11 px-5 text-[0.95rem]")}
                >
                  Build my resume
                  <ArrowRightIcon aria-hidden="true" data-icon="inline-end" />
                </Link>
                <Link
                  href="#how-it-works"
                  className={cn(
                    buttonVariants({ variant: "ghost", size: "lg" }),
                    "h-11 px-4 text-[0.95rem]",
                  )}
                >
                  See how it works
                </Link>
              </div>
            </div>

            <EvidenceDemo />
          </div>
        </section>

        {/* How it works */}
        <Section
          id="how-it-works"
          eyebrow="How it works"
          title="From what you did to a resume you can stand behind."
        >
          <ol className="grid gap-px overflow-hidden rounded-2xl border bg-border sm:grid-cols-2 lg:grid-cols-4">
            {STEPS.map((step, index) => (
              <li key={step.title} className="flex flex-col gap-3 bg-card p-6 sm:p-7">
                <span className="font-heading text-4xl text-primary" aria-hidden="true">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <h3 className="text-base font-semibold">{step.title}</h3>
                <p className="text-sm leading-relaxed text-muted-foreground">{step.body}</p>
              </li>
            ))}
          </ol>
        </Section>

        {/* Principles */}
        <Section
          id="principles"
          eyebrow="Our one rule"
          title={
            <>
              It improves the wording. <em className="text-primary">Never the facts.</em>
            </>
          }
          intro="Recruiters can ask about any line on your resume. Every line Workaholic writes traces back to something you told it."
        >
          <div className="grid gap-4 md:grid-cols-2">
            <PrincipleList title="Workaholic will" items={WILL} tone="positive" />
            <PrincipleList title="Workaholic won't" items={WONT} tone="negative" />
          </div>
        </Section>

        {/* Honest ATS */}
        <Section id="ats" eyebrow="Honest ATS analysis" title="A score that shows its working.">
          <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-14">
            <div className="space-y-4 text-[1.05rem] leading-relaxed text-muted-foreground">
              <p>
                The Workaholic ATS Compatibility Score comes from checks you can read, not a number
                pulled from thin air. Every point comes with the reason behind it and what to fix.
              </p>
              <p className="border-l-2 border-primary pl-4 text-foreground">
                No score can guarantee an interview. Employers use different systems, configured in
                different ways — anyone promising otherwise is guessing.
              </p>
            </div>
            <ul className="grid content-start gap-2 sm:grid-cols-2">
              {ATS_CHECKS.map((check) => (
                <li
                  key={check}
                  className="flex items-center gap-2.5 rounded-lg border bg-card px-3.5 py-3 text-sm"
                >
                  <CheckIcon className="size-4 shrink-0 text-primary" aria-hidden="true" />
                  {check}
                </li>
              ))}
            </ul>
          </div>
        </Section>

        {/* Closing CTA */}
        <section className="px-4 pb-24 sm:px-6">
          <div className="relative mx-auto max-w-6xl overflow-hidden rounded-3xl bg-primary px-6 py-16 text-center text-primary-foreground sm:px-12 sm:py-20">
            <div
              aria-hidden="true"
              className="pointer-events-none absolute inset-0 opacity-[0.07] [background-image:repeating-linear-gradient(to_bottom,transparent_0,transparent_31px,currentColor_31px,currentColor_32px)]"
            />
            <h2 className="relative font-heading text-4xl tracking-tight sm:text-6xl">
              Start with what&apos;s true.
            </h2>
            <p className="relative mx-auto mt-4 max-w-md text-primary-foreground/75">
              Tell Workaholic what you&apos;ve done. It&apos;ll help you say it well.
            </p>
            <Link
              href={routes.signup}
              className={cn(
                buttonVariants({ size: "lg" }),
                "relative mt-8 h-11 bg-primary-foreground px-5 text-[0.95rem] text-primary hover:bg-primary-foreground/90",
              )}
            >
              Create your account
              <ArrowRightIcon aria-hidden="true" data-icon="inline-end" />
            </Link>
          </div>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}

function SiteHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-transparent bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/65">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Logo />
        <nav aria-label="Main" className="flex items-center gap-1 sm:gap-2">
          <Link
            href="#how-it-works"
            className={cn(buttonVariants({ variant: "ghost" }), "hidden h-9 md:inline-flex")}
          >
            How it works
          </Link>
          <Link
            href="#principles"
            className={cn(buttonVariants({ variant: "ghost" }), "hidden h-9 md:inline-flex")}
          >
            Principles
          </Link>
          <Link href={routes.login} className={cn(buttonVariants({ variant: "ghost" }), "h-9")}>
            Sign in
          </Link>
          <Link href={routes.signup} className={cn(buttonVariants(), "h-9 px-3.5")}>
            Get started
          </Link>
        </nav>
      </div>
    </header>
  );
}

function SiteFooter() {
  return (
    <footer className="border-t">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div className="flex items-center gap-3">
          <Logo className="[&_span]:text-lg" />
          <span>© {new Date().getFullYear()}</span>
        </div>
        <nav aria-label="Footer" className="flex gap-5">
          <Link href={routes.login} className="hover:text-foreground">
            Sign in
          </Link>
          <Link href={routes.signup} className="hover:text-foreground">
            Create account
          </Link>
        </nav>
      </div>
    </footer>
  );
}

function Section({
  id,
  eyebrow,
  title,
  intro,
  children,
}: {
  id: string;
  eyebrow: string;
  title: ReactNode;
  intro?: string;
  children: ReactNode;
}) {
  return (
    <section
      id={id}
      aria-labelledby={`${id}-title`}
      className="scroll-mt-20 px-4 py-20 sm:px-6 sm:py-24"
    >
      <div className="mx-auto max-w-6xl">
        <div className="mb-12 max-w-2xl">
          <p className="font-mono text-xs tracking-[0.14em] text-primary uppercase">{eyebrow}</p>
          <h2
            id={`${id}-title`}
            className="mt-3 font-heading text-4xl leading-[1.05] tracking-tight sm:text-5xl"
          >
            {title}
          </h2>
          {intro ? (
            <p className="mt-4 text-lg leading-relaxed text-muted-foreground">{intro}</p>
          ) : null}
        </div>
        {children}
      </div>
    </section>
  );
}

function PrincipleList({
  title,
  items,
  tone,
}: {
  title: string;
  items: string[];
  tone: "positive" | "negative";
}) {
  const Icon = tone === "positive" ? CheckIcon : MinusIcon;
  return (
    <div
      className={cn(
        "rounded-2xl border p-6 sm:p-8",
        tone === "positive" ? "bg-card" : "bg-secondary/60",
      )}
    >
      <h3 className="font-heading text-2xl">{title}</h3>
      <ul className="mt-5 space-y-3.5">
        {items.map((item) => (
          <li key={item} className="flex gap-3 text-[0.95rem] leading-snug">
            <span
              className={cn(
                "mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full",
                tone === "positive"
                  ? "bg-primary text-primary-foreground"
                  : "bg-destructive/12 text-destructive",
              )}
            >
              <Icon className="size-3" aria-hidden="true" />
            </span>
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
