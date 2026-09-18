# ADR-010 — No resume from an incomplete record; a guide walks people through it

**Status:** Accepted · 2026-09-19

## Context

Two problems showed up in use. First, a resume could be written from a record with no education
or no contact details, and the only thing that noticed was the ATS check — *after* the document
existed and might already have been sent. Second, the interview that fills the record was hard to
find (only inside a resume) and started with work history, so someone who would rather talk than
fill in forms had no obvious way in, and it never asked for a name, an email or a grade.

## Decision

1. **Writing is gated on readiness.** `services/resume/readiness.py` decides, in code, whether the
   record holds what a document needs. A resume needs a name, an email or phone number, at least
   one school, at least one skill, and at least one role *or* project with a sentence about what
   was done. A cover letter needs the name, contact and something done. Generation refuses with
   `PROFILE_INCOMPLETE` and lists what is missing before any model is called. The same checklist
   is served at `GET /profile/readiness` and shown in front of the "Write" button, so the button is
   disabled with the reasons beside it rather than failing after a click.
2. **Experience *or* projects, deliberately.** A student who has never had a job must still be
   able to build a resume from what they built. Requiring a job would push them to invent one,
   which is the one thing this product exists to prevent.
3. **The interview is now a guide, reachable on its own.** `/assistant` starts a conversation that
   belongs to no resume. Its order is the order a person fills in a resume: name, contact, school,
   grade, then work, projects, skills. The questions for those opening topics are fixed templates —
   there is nothing for a model to phrase in "what's your name", the grade question can say plainly
   that "skip" is fine, and the work question tells someone with no job that "no" is a fine answer.
4. **The new facts are grounded like every other.** A name must be words the person said. An email
   is kept only if the answer spells it out, typed or spoken ("ada at gmail dot com"). A phone
   number's digits must appear in order, so a country code the person never gave is dropped. A
   grade must be stated in every part, so "4.5 out of 5" can never become "3.6/4". Basics fill only
   empty fields: a name someone typed is never replaced by one mentioned in passing.
5. **Voice both ways, at no cost.** Questions are read aloud with the browser's own speech
   synthesis — no provider, no audio leaving the device, no Azure resource. Answers are still
   spoken through the existing `gpt-4o-transcribe` deployment and land in the answer box to be
   checked. Reading stops the moment the microphone opens, so it never transcribes itself.
6. **A CV can be dropped in mid-conversation.** The upload goes through the same review as on the
   profile page (nothing is added until it is ticked), then `POST /interviews/{id}/continue` asks
   the next question from the record as it now stands, skipping whatever the document answered.

## Consequences

- Someone can no longer produce a resume that is missing its education section. They can still
  skip any question in the conversation; the closing message then says exactly what the record
  still needs, instead of telling them they are done.
- The grade is optional everywhere. It is printed only when recorded, next to the school.
- The guided order means an interview started from a resume also asks for the basics first when
  they are missing. That is the right order for a resume either way.
- No new Azure resource and no new cost: speech output is the browser's, and the only new model
  work is a few extra fields on an extraction call that was already being made.
