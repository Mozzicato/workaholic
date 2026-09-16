# ADR-002 — PostgreSQL is the source of truth; Redis is disposable

**Status:** Accepted · 2026-09-16

## Context

Career data (profiles, evidence, resumes, versions) must survive any infrastructure event.
The app also needs a queue broker, rate limiting and short-lived state.

## Decision

- All durable application state lives in PostgreSQL (Azure Database for PostgreSQL
  Flexible Server in production), managed through SQLAlchemy models and Alembic migrations.
  The application never creates or alters schema at startup.
- Redis is used only for the Celery broker, caching, rate limiting, locks and temporary
  state. The application must stay logically correct if Redis is wiped.
- Background job state that users rely on is persisted in PostgreSQL; Celery's result
  backend is disabled.

## Consequences

- Production Redis can be the cheapest option (a small container) because losing it only
  loses in-flight work, which is re-derivable from PostgreSQL.
- Every migration is reviewed; CI runs `alembic check` to catch model/migration drift.
