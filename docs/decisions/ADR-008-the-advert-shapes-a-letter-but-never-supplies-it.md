# ADR-008 — A job advert may shape a cover letter, but never supply a claim to it

**Status:** Accepted · 2026-09-18

## Context

Cover letters are not in the PRD; they were asked for after the five phases shipped. The domain
already had most of what they need — a career record, evidence, versioned documents, a renderer
and a PDF pipeline — so the question was not how to build one, but where the new risk is.

It is in the advert. A cover letter is written against a job description, and a job description
is a list of things the employer wants. Hand both to a model and the natural, fluent, disastrous
output is a letter that answers the advert point by point: "I have deep Kubernetes experience,
having run production systems for millions of users" — written for a student who has done none of
those things. Nothing about that sentence looks invented. It looks like a good cover letter.

## Decision

1. **A cover letter is a `DocumentType`, not a new subsystem.** It reuses the resume's record,
   versioning, preview, PDF and ownership rules. Generation and rendering dispatch on the type.
2. **The advert is context, never a source.** It is sent to the model, labelled as what the
   employer wants rather than what the candidate has done, and it is deliberately excluded from
   the material every claim is checked against.
3. **The checks are the same ones a resume uses.** Numbers, names and claim words must be present
   in the candidate's own sentences. The company, the role and the hiring manager are added as
   permitted names because the candidate supplied them.
4. **Three paragraphs, each cited.** The document records which profile items a paragraph drew on,
   so a letter is as traceable as a resume.
5. **The date is written into the document**, not generated at render, so a version renders
   identically forever.
6. **The letter has one layout.** Templates vary a resume's density and section order; a letter
   has neither.
7. **Shared code was moved, not copied.** Reading the record and saving a version are one module
   each now, used by both documents.

## Consequences

- Letters come out plainer than the genre expects. A model asked not to invent enthusiasm writes
  "I am applying for this role" rather than "I have long admired your work in logistics". That is
  the intended trade, and it is the same trade the resume makes.
- Where the candidate's record is thin, the letter is thin. The fix is to add to the record, which
  is what the interview is for — not to let the letter fill the gap.
- A letter can still be refused outright, which for a job application is a sharper interruption
  than for a draft resume. The refusal names what was claimed, so the user can decide whether to
  record it as fact or leave it out.
- Verified against the live model with an advert deliberately full of bait (Go, Kubernetes, AWS,
  Kafka, "millions of users"). The letter claimed none of them.
