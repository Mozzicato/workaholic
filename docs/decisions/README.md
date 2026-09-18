# Architecture Decision Records

Significant architectural decisions, with the context that led to them. Add a new record
rather than editing an accepted one; mark superseded records as such.

| ADR | Decision |
| --- | --- |
| [001](ADR-001-azure-container-apps-for-backend.md) | Azure Container Apps for the API and workers |
| [002](ADR-002-postgresql-source-of-truth-redis-ephemeral.md) | PostgreSQL is the source of truth; Redis is disposable |
| [003](ADR-003-supabase-auth-verified-locally.md) | Supabase Auth, verified locally with asymmetric keys |
| [004](ADR-004-ai-provider-abstraction-azure-foundry.md) | AI provider abstraction with Azure Foundry as the primary provider |
| [005](ADR-005-resume-generation-facts-from-the-record.md) | The model writes wording; the record supplies the facts |
| [006](ADR-006-the-interview-asks-what-the-record-lacks.md) | Code chooses the interview question; the model only phrases it |
| [007](ADR-007-voice-is-an-interface-not-an-authority.md) | Voice is an interface over the interview; the transcript is not the record |
| [008](ADR-008-the-advert-shapes-a-letter-but-never-supplies-it.md) | A job advert may shape a cover letter, but never supply a claim to it |
| [009](ADR-009-matching-tailoring-and-ats-are-deterministic.md) | Matching, tailoring and the ATS score are deterministic; uploads are proposals |

Every section of the PRD is now built. New decisions get a new record.
