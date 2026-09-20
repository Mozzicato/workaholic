# ADR-012 — Feedback, sent-in templates, and an admin dashboard that cannot read anyone's resume

**Status:** Accepted · 2026-09-20

## Context

Three things were missing for anyone actually running Workaholic: a way for users to say something
to the people who build it, a way for the many people who already have a template they like to
offer it, and a way for the operator to see whether any of this is working. All three touch the
one thing the product is built around: a person's record is theirs.

## Decision

1. **An administrator is named in configuration, not in the database.** `ADMIN_EMAILS` (set in
   Terraform) lists verified addresses. Empty means nobody, which is the right default: an
   operator is named deliberately. The check reads the *running application's* settings, not the
   environment, so a request is answered from the configuration the app was started with.
2. **The dashboard counts; it never reads.** Accounts, records ready for a resume, resumes,
   drafts, conversations, imports, jobs, templates in use, sign-ups per day, and the messages
   people chose to send. No resume, profile section, interview answer or job advert is reachable
   through any admin endpoint. A test asserts that the stats response contains none of a
   prepared record's content, and the production check asserts it against the live service.
   Readiness is computed with the same code that refuses to write an incomplete resume, so the
   headline number cannot drift from what people experience.
3. **Feedback carries the page it was written on**, and survives the account that sent it: a
   complaint is worth acting on after the person has gone. An administrator can mark it done or
   delete it outright.
4. **A sent-in template is a message, not an upload to parse.** Someone sends a PDF or Word file
   and a note; a person looks at it and builds the template. Deliberately not automatic —
   approximating an arbitrary design and presenting it as "their template" would be worse than
   saying plainly that a human does this, and the product's whole claim is that it does not
   fabricate. The file is stored in the database (it is small, so this needs no new storage and
   no new Azure resource), is never read into anyone's record, and is deleted once handled.
5. **An account can erase itself** (`DELETE /api/v1/me`), and an administrator can erase another
   account but not their own. Erasing takes the record, resumes, drafts, conversations and
   evidence; it leaves feedback, with its owner detached.

## Consequences

- The operator can answer "is anyone using this, and what are they complaining about?" without
  ever being able to answer "what does Amara's resume say?".
- Storing sent-in files in Postgres is fine at this size and keeps Stage 3 (blob storage)
  unnecessary. If template requests ever become common, that trade should be revisited.
- Two operational lessons, both learned the hard way here:
  - A local `.env` hid a bug that CI caught: the admin check was loading settings from the
    environment at request time, so on a machine without an `.env` every `/me` call failed.
    Request paths now take settings from `app.state`, and `get_settings()` is called only when
    the application starts.
  - Applying a *saved* Terraform plan after a deployment rolled the API image back one commit,
    because the saved plan carried the image recorded when it was planned. `ignore_changes` only
    protects a fresh plan. Plan and apply in one step, or re-deploy afterwards.
