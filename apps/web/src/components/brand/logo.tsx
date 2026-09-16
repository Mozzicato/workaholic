import Link from "next/link";

import { cn } from "@/lib/utils";

type Tone = "default" | "inverse";

/** The Workaholic mark: a document page with a verification tick. */
export function LogoMark({ className, tone = "default" }: { className?: string; tone?: Tone }) {
  const inverse = tone === "inverse";
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={cn("size-7 shrink-0", className)}>
      <path
        d="M8 3.5h11.5L25 9v18.5a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 7 27.5v-22A2 2 0 0 1 8 3.5Z"
        className={inverse ? "fill-primary-foreground" : "fill-primary"}
      />
      <path
        d="M19.5 3.5V8a1 1 0 0 0 1 1H25"
        className={inverse ? "fill-primary/20" : "fill-primary-foreground/25"}
      />
      <path
        d="M11 14.5h7.5M11 18h10"
        className={inverse ? "stroke-primary/60" : "stroke-primary-foreground/70"}
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <path
        d="m11.5 22.6 2.2 2.1 4.6-4.6"
        className={inverse ? "stroke-primary" : "stroke-highlight"}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
    </svg>
  );
}

export function Logo({
  href = "/",
  className,
  tone = "default",
}: {
  href?: string;
  className?: string;
  tone?: Tone;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "inline-flex items-center gap-2 rounded-md outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
        className,
      )}
    >
      <LogoMark tone={tone} />
      <span className="font-heading text-[1.45rem] leading-none tracking-tight">Workaholic</span>
    </Link>
  );
}
