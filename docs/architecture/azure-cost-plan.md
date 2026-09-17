# Azure cost plan

**Budget:** Azure for Students, $100 credit, 12 months. When the credit runs out the subscription
is **disabled**, not billed — so overspending means an outage, not a surprise invoice.
**Region:** France Central (allowed by the subscription policy, cheapest of the allowed regions
for PostgreSQL, all required services available; network latency from Lagos was similar across
all allowed regions).
**Rule:** infrastructure is created in stages, only when a shipped feature needs it, and only
after the owner approves each resource.

Prices below are list prices from the Azure Retail Prices API for `francecentral`, retrieved
2026-09-17, and are estimates, not guarantees. A month is ~730 hours.

## Legend

- **Verified** — confirmed from Microsoft documentation or the retail price API on the date above.
- **Unverified** — plausible but not confirmed; treated as paid until proven otherwise.

## Resources

| Resource | Purpose | Free allowance | Expected cost | Uses $100 credit | Cheaper practical alternative |
| --- | --- | --- | --- | --- | --- |
| Resource group, provider registration | Organisation | Free (not billed resources) | $0 | No | — |
| Cost Management budget + alerts | Detect unexpected spend | No charge for budgets | $0 | No | Weekly CLI cost query if the offer doesn't support budgets |
| **Microsoft Foundry resource** (`AIServices`, S0) | LLM inference | No standing charge — "free to use and explore" (**verified**) | Pay per token only: ~$0.02–0.10 per resume flow depending on model (to be measured by the benchmark) | **Yes** (models sold by Azure) | Free dev tiers of other providers (Gemini/Groq) for experiments only — not for real user data |
| **PostgreSQL Flexible Server**, Burstable B1ms, 32 GB | Source of truth | 12-month free-account allowance **unverified for Azure for Students** | $0.019/h compute (**verified**) ≈ $13.87/mo + $0.133/GB-mo storage ≈ $4.26/mo → **≈ $18/mo if always on**. Stopped: compute stops billing, storage continues, auto-restarts after 7 days (**verified**) | Yes | Stop it when not testing during development; smallest storage size; no HA, no geo-redundant backup |
| **Container Apps** (Consumption), API + worker | Run the API and worker | Per **subscription** per month, shared by all apps: 180,000 vCPU-s, 360,000 GiB-s, 2M requests (**verified**). Scaled to zero = no charge (**verified**) | Active $0.000024/vCPU-s, idle $0.000003/vCPU-s, memory $0.000003/GiB-s, requests $0.40/M after free grant (**verified**). With scale-to-zero at low traffic: likely within the grant | Only above the grant | This is already the cheapest option; keep `minReplicas=0` |
| **Container Registry**, Basic | Store Docker images | 12-month free-account allowance **unverified for Azure for Students** | $0.1666/day (**verified**) ≈ **$5/mo** + $0.10/GB-mo over the included storage | Yes | Pull images from GitHub Container Registry (free for the repo's own images) — requires a registry credential or public image; decide at deploy time |
| **Log Analytics** (Container Apps logs) | Operational logs | First 5 GB ingestion/month at $0 (**verified** tier pricing) | $2.76/GB after 5 GB; retention beyond included period $0.12/GB-mo (**verified**) | Only above free tier | Log only structured metadata (already enforced), set a daily cap, 30-day retention |
| **Blob Storage**, Hot LRS | Uploaded resumes, generated PDFs | 12-month free-account allowance **unverified for Azure for Students** | $0.0192/GB-mo, reads $0.0047/10K (**verified**) — cents at MVP volume | Yes | None needed |
| **Redis** | Celery broker, rate limiting, cache | See options below | See options below | Depends on option | See options below |
| Sentry | Error monitoring | Free developer plan (external) | $0 initially | No | — |
| Vercel | Next.js frontend | Hobby plan (external) | $0 initially | No | — |
| Supabase Auth | Authentication | Free plan (external) | $0 initially | No | — |

### Redis options (needed only when background jobs or rate limiting ship)

| Option | Cost | Fit |
| --- | --- | --- |
| Upstash free | $0: 256 MB, 500K commands/month (from Upstash's announcement; re-verify) | Fine for rate limiting and cache. **Not enough for an always-on Celery worker**: Celery's Redis transport polls continuously, which can exceed 500K commands/month on its own |
| Redis Cloud free | $0: 30 MB; connection, throughput and region limits not stated on the pricing page (**unverified**) | Possible Celery broker for low volume; verify limits before relying on it |
| Redis container in Container Apps (0.25 vCPU / 0.5 GiB, 1 replica) | ≈ $4/mo if billed idle, ≈ $14/mo if billed active — and it consumes the shared free grant the API and worker also need | Simple and in-region, but always-on |
| Azure Managed Redis | Highest fixed monthly cost | **Not used** for the MVP |

Decision deferred until the worker ships; the API already runs without Redis (`REDIS_URL` is
optional and `/ready` only checks configured dependencies).

## Rollout stages (each needs explicit approval before creation)

| Stage | Creates | Trigger | Expected monthly cost |
| --- | --- | --- | --- |
| **0. Guardrails** ✅ | Register `Microsoft.CognitiveServices`; resource group `workaholic-prod-rg`; annual $100 and monthly $20 budgets with alerts | Done 2026-09-17 | $0 |
| **1. AI** ✅ | Foundry resource + 2 Global Standard deployments (`gpt-5-mini`, `gpt-4.1-mini`; Data Zone quota is 0); your user has *Cognitive Services OpenAI User* | Done 2026-09-17 | Benchmark ≈ $0.04; $0 idle |
| **2. First deployment** ✅ | PostgreSQL 17 B1ms (Entra-only, France Central); Container Registry Basic; Container Apps environment + API app (scale to zero) + migration job (**Germany West Central** — France Central refused environment creation for this subscription); managed identities + least-privilege roles; Log Analytics capped at 0.1 GB/day; GitHub OIDC deploy identity | Started 2026-09-17 at the owner's request, ahead of Phase 2 | ≈ $23/mo with the DB always on (≈ $18 DB + ≈ $5 registry); ≈ $5–9/mo if the DB is stopped outside testing. Cross-region DB traffic: cents |
| 3. Files | Storage account (private containers) | When uploads/PDF export ship | Cents |
| 4. Background work | Redis option above + worker app (scale to zero on queue length) | When the first Celery task ships | $0–14/mo depending on option |

**How long $100 lasts** can only be estimated from measured usage. With Stage 2 running
continuously the fixed cost is roughly $23/month before AI usage; stopping the database outside
testing cuts that substantially. Actual spend is reviewed from Cost Management after the first
week of each stage and this document is updated with real numbers.

## Cost controls built into the code and configuration

- AI: output tokens capped per call (`AI_MAX_OUTPUT_TOKENS`), reasoning effort configurable,
  structured-output repairs capped (`AI_STRUCTURED_OUTPUT_ATTEMPTS`), pay-per-token deployments
  only, per-call token usage logged for cost attribution.
- Redis optional until needed; readiness never calls AI.
- Container Apps replica counts, database SKU and storage size will be Terraform variables, not
  hard-coded.
- Rate limits (Phase 9) protect AI spend from abuse.
