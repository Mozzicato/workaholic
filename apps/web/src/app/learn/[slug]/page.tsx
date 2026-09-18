import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ARTICLES, findArticle } from "@/features/learn/content";
import { routes } from "@/lib/routes";

export function generateStaticParams() {
  return ARTICLES.map((article) => ({ slug: article.slug }));
}

export async function generateMetadata({ params }: PageProps<"/learn/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const article = findArticle(slug);
  return article ? { title: article.title, description: article.summary } : { title: "Not found" };
}

export default async function ArticlePage({ params }: PageProps<"/learn/[slug]">) {
  const { slug } = await params;
  const article = findArticle(slug);
  if (!article) notFound();

  return (
    <article className="space-y-8">
      <div>
        <Link
          href={routes.learn}
          className="text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          ← All guides
        </Link>
      </div>

      <header className="space-y-2">
        <h1 className="font-heading text-4xl tracking-tight sm:text-5xl">{article.title}</h1>
        <p className="text-muted-foreground">
          {article.summary} · {article.minutes} min read
        </p>
      </header>

      <div className="space-y-8">
        {article.sections.map((section) => (
          <section key={section.heading} className="space-y-3">
            <h2 className="font-heading text-2xl">{section.heading}</h2>
            {section.paragraphs.map((paragraph) => (
              <p key={paragraph} className="max-w-prose leading-relaxed">
                {paragraph}
              </p>
            ))}
            {section.list ? (
              <ul className="max-w-prose list-disc space-y-1.5 pl-5 leading-relaxed">
                {section.list.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
          </section>
        ))}
      </div>

      <footer className="rounded-xl border bg-card p-5 text-sm text-muted-foreground sm:p-6">
        Ready to put this to work?{" "}
        <Link href={routes.profile} className="underline underline-offset-4 hover:text-foreground">
          Add it to your career record
        </Link>{" "}
        — Workaholic writes from what you record, and nothing else.
      </footer>
    </article>
  );
}
