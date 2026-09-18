import type { Metadata } from "next";
import Link from "next/link";

import { ARTICLES } from "@/features/learn/content";

export const metadata: Metadata = {
  title: "Learn",
  description: "Short, plain guides to resumes, ATS and writing about your own work.",
};

export default function LearnPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="font-heading text-4xl tracking-tight sm:text-5xl">Learn</h1>
        <p className="max-w-prose leading-relaxed text-muted-foreground">
          Short guides on writing about your own work. No tricks, no promises about beating
          anyone&apos;s software — just what these documents are for and what makes them read well.
        </p>
      </header>

      <ul className="divide-y overflow-hidden rounded-xl border bg-card">
        {ARTICLES.map((article) => (
          <li key={article.slug}>
            <Link
              href={`/learn/${article.slug}`}
              className="block px-5 py-4 outline-none transition-colors hover:bg-muted/60 focus-visible:bg-muted/60"
            >
              <span className="flex flex-wrap items-baseline justify-between gap-2">
                <span className="font-medium">{article.title}</span>
                <span className="text-xs text-muted-foreground">{article.minutes} min read</span>
              </span>
              <span className="mt-0.5 block text-sm text-muted-foreground">{article.summary}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
