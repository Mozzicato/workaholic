import { describe, expect, it } from "vitest";

import { ARTICLES, findArticle } from "./content";

describe("the learning section (PRD §46)", () => {
  it("covers every page the PRD lists", () => {
    expect(ARTICLES.map((article) => article.title)).toEqual([
      "What is a resume?",
      "Resume or CV?",
      "What is an ATS?",
      "Writing better experience bullets",
      "How to describe projects",
      "How to quantify achievements",
      "Common resume mistakes",
    ]);
  });

  it("gives every article a unique address and real content", () => {
    const slugs = ARTICLES.map((article) => article.slug);
    expect(new Set(slugs).size).toBe(slugs.length);
    for (const article of ARTICLES) {
      expect(article.sections.length).toBeGreaterThan(1);
      expect(article.summary.length).toBeGreaterThan(10);
    }
  });

  it("never promises what nobody can promise", () => {
    const text = JSON.stringify(ARTICLES).toLowerCase();
    for (const forbidden of ["guaranteed", "beat the ats", "ats-proof", "100% pass"]) {
      expect(text).not.toContain(forbidden);
    }
  });

  it("finds an article by its address, and nothing for an unknown one", () => {
    expect(findArticle("what-is-ats")?.title).toBe("What is an ATS?");
    expect(findArticle("not-a-real-page")).toBeUndefined();
  });
});
