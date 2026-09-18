# ADR-005 — The model writes wording; the record supplies the facts

**Status:** Accepted · 2026-09-18

## Context

The product's promise is that a Workaholic resume contains nothing the user did not say (PRD §2.1,
§2.2). Language models are fluent and will, unprompted, round a number up, promote "helped with" to
"owned", or add a plausible employer. Asking a model to write a resume from a profile and trusting
the result would break the promise on the first draft, silently, in a document the user then sends
to an employer.

Two weaker designs were rejected:

- **Prompting alone.** A system prompt that forbids invention reduces it but cannot prevent it, and
  nothing detects the cases that slip through.
- **A model checking the model.** A second pass asking "is this supported?" fails in exactly the
  cases that matter: a model that invented a metric will confirm it.

## Decision

1. **Facts never reach the model.** Employers, titles, dates, locations, schools, certifications
   and skills are copied from the candidate profile into the resume document by application code.
   The model receives only sentences the user wrote themselves, plus the target role.
2. **The model rewrites, one line at a time.** It returns each bullet by id, and a summary. It
   cannot add, merge, drop or reorder lines, because the document is assembled from the record and
   the rewrites are matched back to their sources by id.
3. **Every rewrite is checked deterministically** (`app.services.resume.validation`) against the
   sentence it came from: numbers must already be present, names and acronyms must already be
   present, and a vocabulary of impact and seniority words is refused unless the source supports
   it. The checks are pure functions, so they are exhaustively testable and cost nothing to run.
4. **A failure is named back to the model once.** If the second attempt still adds something,
   generation is blocked with a 422 that lists what was added. Nothing is written.
5. **Evidence a model proposed is not usable.** A profile item carrying `MODEL_INFERRED` or
   `UNVERIFIED` evidence is left out of the document entirely until the user confirms it (PRD §15).
6. **Versions are immutable** and record the prompt version and model, so a prompt regression can
   be traced to the documents it produced.
7. **The renderer owns formatting** (PRD §19, §21). Validated JSON goes to HTML through three
   deterministic single-column templates, and Chromium prints that HTML to PDF. The model never
   produces markup.

## Consequences

- A faithful but plain draft is the normal outcome. That is the intended trade: the tool makes
  weak writing read better, and asks for more detail rather than inventing it.
- The checks are conservative and can refuse a rewrite that a careful human would allow — for
  example promoting "scaling work" to "scaled". The retry usually resolves it, and a false refusal
  costs a regenerate, while a false acceptance costs the user their credibility in an interview.
- Generation is synchronous: one request, one document, and the user learns immediately if the
  draft was refused. Moving it to the Celery worker becomes worthwhile when generation gets slower
  or its cost needs smoothing, not before.
- The PDF is printed by the **Chromium headless shell** rather than full Chromium: the same output
  for a third of the image size. Peak memory measured with the whole app loaded is 291 MiB, so the
  container stays at 0.25 vCPU / 0.5 GiB and no Azure resource changes. Renders are capped at two
  at a time so printing a page can never take the API down with it.
- The image grows to ~1.35 GB, which lengthens a cold start after scale-to-zero. Accepted for now;
  if it becomes a problem the renderer moves to its own app rather than the API keeping a browser.
