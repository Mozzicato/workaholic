# ADR-006 — Code chooses the question; the model only phrases it

**Status:** Accepted · 2026-09-18

## Context

The interview is where facts enter Workaholic (PRD §23, §24). Everything downstream — the career
record, evidence, every resume — inherits whatever it collects, so a mistake here is not a bad
sentence, it is a false claim that survives into a document someone sends to an employer.

The obvious design is to hand a model the transcript and let it run the conversation. That fails
in three ways this project cannot accept: the interview's behaviour becomes unpredictable and
essentially untestable; every turn costs a model call whether or not it was useful; and a chatty
model drifts into asking leading questions — "did you use Docker for that?" — which put words in
the candidate's mouth, exactly what PRD §2.2 forbids.

## Decision

1. **Gap analysis is code** (`app.services.interview.gaps`). It reads the record and returns what
   is missing, ordered by the priority list in PRD §24. It is pure, so the interview's behaviour
   is pinned by tests with no model involved.
2. **The model phrases one question about one gap**, with the recent transcript for context. If
   its question introduces a name or a number that is not already in the record or the
   conversation, it is discarded in favour of a plain question for that gap.
3. **Plain questions exist for every gap**, so the interview runs with AI disabled or unavailable.
   Collecting the record matters more than the phrasing.
4. **Extraction is grounded against the answer.** The model fills a fixed shape from one answer,
   and every field is then checked against what the person actually said, by the same
   deterministic checks that guard resume wording. Names are checked word by word, because a
   standalone "Google" is capitalised like any first word. Dates keep only the year unless the
   month is in the answer too.
5. **The user is told what was dropped**, unless the record already holds it — in which case it
   was a repetition, not an invention.
6. **Everything recorded is `USER_PROVIDED` evidence** carrying the id of the message it came
   from, so a line on a finished resume traces back to the sentence that produced it.
7. **An answer that instructs the writer is refused**, as in generation: text that says "make
   this sound senior" would otherwise supply its own vocabulary to the checks that follow.
8. **A session is capped** at 25 questions, so one conversation cannot run up an unbounded bill.

## Consequences

- The interview is cheap and predictable: two model calls per turn, both narrow, and a hard
  ceiling per session.
- It cannot ask a genuinely creative follow-up that no gap covers. In exchange it never asks a
  leading question, and what it does ask is derived from the person's actual record.
- Question quality depends on the model, but question *safety* does not.
- Four faults found by running a real interview rather than by testing: claim words were
  disqualifying good questions (asking about users is not claiming users); concatenating the
  model's "bullets" and "outcomes" stored the same fact twice; "docker for running things
  locally" was stored as a tool; and repeating a recorded fact was reported as an invention.
  Each is now covered by a test.
