# Workaholic

An evidence-first resume builder. Workaholic interviews people about what they've actually
done, turns their answers into evidence they confirm, and writes ATS-readable resumes from
it — improving the wording, never the facts.

- Product spec: [PRD.md](PRD.md)
- Infrastructure spec: [AZURE.md](AZURE.md)
- Decisions: [docs/decisions](docs/decisions/README.md)

## Repository

```text
apps/
  api/        FastAPI API + Celery worker (Python 3.12, uv)
  web/        Next.js 16 web app (TypeScript, pnpm)
infrastructure/
  docker/     Local container init scripts
docs/
  decisions/  Architecture decision records
docker-compose.yml   Local PostgreSQL, Redis and Azurite
```

## Prerequisites

| Tool | Version |
| --- | --- |
| Node.js | 22+ (24 recommended) |
| pnpm | 12 |
| Python | 3.12 |
| uv | 0.12+ |
| Docker Desktop | running |

## First-time setup

```bash
# 1. Environment
cp .env.example .env                       # fill in the Supabase values
cp apps/web/.env.example apps/web/.env.local   # publishable key only — never a secret

# 2. Dependencies
pnpm install
cd apps/api && uv sync && cd ../..

# 3. Local infrastructure (PostgreSQL, Redis, Azurite)
pnpm infra:up

# 4. Database schema
pnpm db:migrate
```

In the Supabase dashboard, under **Authentication → URL Configuration**, set the Site URL to
`http://localhost:3000` and add `http://localhost:3000/**` as a redirect URL.

## Running locally

Run each in its own terminal:

```bash
pnpm dev:api      # API on http://localhost:8080 (docs at /docs)
pnpm dev:web      # Web on http://localhost:3000
pnpm dev:worker   # Celery worker (only needed once background jobs exist)
```

Local services bind to `127.0.0.1`. Use `127.0.0.1` rather than `localhost` in connection
URLs — on Windows, `localhost` tries IPv6 first and each new connection stalls for ~2 seconds.

## Checks

```bash
pnpm check:api    # ruff format + lint, mypy --strict, pytest (needs pnpm infra:up)
pnpm check:web    # eslint, tsc, vitest
```

CI (`.github/workflows/ci.yml`) runs the same checks plus a migration drift check, a
production Docker build and a Next.js production build on every pull request.

## Ground rules

These come from the PRD and are enforced in review:

- The AI may improve expression, never reality. No invented metrics, employers, dates,
  skills or achievements.
- Identity comes only from a verified token. Every user-owned query is scoped to the
  authenticated user.
- PostgreSQL is the source of truth. Redis is disposable.
- No mock data, fake AI output or placeholder functionality presented as real.
- Never log resume content, job descriptions, tokens or audio.
- Secrets never enter Git, Docker images or the browser bundle.
