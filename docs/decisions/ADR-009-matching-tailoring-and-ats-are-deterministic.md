# ADR-009 — Matching, tailoring and the ATS score are deterministic; uploads are proposals

**Status:** Accepted · 2026-09-18

## Context

The last PRD sections — job analysis (§31), matching (§32), tailoring (§33), the ATS engine
(§34–35) and document upload (§37) — are the places a resume product is most tempted to flatter
its user. A job wants Kubernetes; the user has none; every one of these features has an easy,
fluent way to make that gap disappear. Each is also a place where a number or verdict is shown to
someone deciding whether to send an application.

## Decision

1. **A model reads the advert; code does everything else.** Job analysis is the only model call:
   it turns prose into required skills, preferred skills and keywords, with the advert delimited
   and labelled as data (PRD §38). The advert is kept verbatim so the user can always see what they
   applied to.
2. **Matching is deterministic.** A requirement is MATCHED only when the candidate listed it as a
   skill or a tool; PARTIALLY_MATCHED when it appears only in what they wrote they did; NOT_FOUND
   otherwise. Words match whole — "Go" never matches "Django" — and the alias table is short on
   purpose, because a wrong equivalence claims a skill the candidate lacks. Matching writes
   nothing.
3. **Tailoring only reorders.** It is not a model call. It moves the most relevant roles,
   projects, bullets and skills to the front, and it structurally cannot reword a line or add
   one. The change summary is computed from what actually moved, and states what can never be
   touched. Requirements the record cannot support are reported as missing, never filled. Every
   tailoring produces a new version; the original is kept.
4. **The ATS score is a checklist, not a prediction.** Five categories of twenty points, every
   check deterministic and explained, and the PDF is actually printed and its text read back out
   — the only honest way to check that a PDF contains text. It is always named "Workaholic ATS
   Compatibility Score" and always shown with its caveat. No string anywhere may promise that a
   resume will pass anything; a test enforces that.
5. **An upload is a proposal.** The file is identified by its bytes, not its name or claimed
   type; it is parsed in memory and never stored. The model reads it into structure; every field
   is then checked against the document's own text, and what the document did not say is dropped
   and shown. Nothing enters the record until the user ticks it, and what they accept is recorded
   as `USER_CONFIRMED` evidence from an uploaded document. An upload never overwrites anything
   the user wrote themselves.

## Consequences

- None of this can make a weak application look strong. It can only make a real one easier to
  read, and tell the user honestly where the gaps are.
- Tailoring feels modest compared with tools that rewrite a resume for every job. That is the
  point: a reordered resume is still true, and a rewritten one has to be checked all over again.
- Storing no uploaded file means no blob storage and no new Azure resource. The trade is that an
  upload cannot be re-parsed later; the user uploads again, which takes seconds.
- Bugs found by running a real CV through a real model, not by the tests written first: a tool
  with punctuation in its name ("Next.js", "C++") was being dropped as unsupported; a
  "Technologies: …" label line was being kept as an achievement; and "BSc Computer Science" was
  printing its field of study twice. A fourth, found by a matching test, was worse: profile items
  created through the API were getting a new id on every read, which would have silently broken
  every evidence link. All four have regression tests.
