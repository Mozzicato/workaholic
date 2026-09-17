# AI platform

**Status:** Implemented (`apps/api/app/services/ai/`). Foundry resource `workaholic-ai-frc` and
two deployments created 2026-09-17 (Stage 1, approved). Keyless access verified end to end.
**Default model:** `gpt-5-mini`, `AI_REASONING_EFFORT=low` (see benchmark results below).
**Last verified against Microsoft documentation:** 2026-09-17.

## Architecture

```text
Workaholic services (interview, generation, tailoring, ATS, parsing)
                 │   depend only on
                 ▼
        LLMProvider interface   generate() · structured_output() · stream()
                 │
     ┌───────────┴──────────────────────────────┐
     ▼                                          ▼
 AzureFoundry (primary)               OpenAI-compatible adapter
 Azure OpenAI v1 API                  Groq · Google AI Studio (Gemini) · Mistral ·
 Entra ID / managed identity          NVIDIA NIM · Hugging Face · direct OpenAI
```

- One adapter (`OpenAICompatibleProvider`) speaks the Chat Completions protocol. Azure's v1
  endpoint and most other providers accept it, so switching provider is configuration.
- Providers that don't speak it (e.g. Anthropic's native API) get their own class implementing
  the same `LLMProvider` protocol — no business logic changes.
- **Chat Completions, not the Responses API.** Microsoft documents that the Responses API stores
  message history at rest; Chat Completions is stateless. Resume content should not be persisted
  by the model service.
- Every call has an `operation` name and an `ait_…` trace ID. Logs record provider, model,
  latency, token usage, finish reason and attempts — **never prompts or completions**.
- `structured_output()` uses strict JSON Schema, validates with Pydantic, and retries once with
  validation feedback (field paths and messages only). Schema validation is necessary but not
  sufficient: callers still run business and evidence validation before persisting anything.
- Errors map to the API contract: `AI_BUSY` (429), `AI_CONTENT_FILTERED`, `AI_INVALID_OUTPUT`,
  `AI_UNAVAILABLE`, `AI_NOT_CONFIGURED`. Provider error text is never shown to users.

## Configuration

| Variable | Purpose | Default |
| --- | --- | --- |
| `AI_PROVIDER` | `azure`, `openai_compatible` or `disabled` | `disabled` |
| `AZURE_AI_ENDPOINT` | `https://<resource>.openai.azure.com` (or `.services.ai.azure.com`) | — |
| `AZURE_AI_MODEL` | **Deployment name** to call (not the catalog model ID) | — |
| `AZURE_AI_AUTH` | `entra_id` (recommended) or `api_key` | `entra_id` |
| `AZURE_AI_API_KEY` | Only when `AZURE_AI_AUTH=api_key` | — |
| `AZURE_CLIENT_ID` | Client ID of the Container App's user-assigned managed identity | — |
| `OPENAI_COMPATIBLE_BASE_URL` / `_API_KEY` / `_MODEL` | Any other provider | — |
| `OPENAI_COMPATIBLE_TOKEN_LIMIT_PARAM` | `max_completion_tokens` or `max_tokens` for older APIs | `max_completion_tokens` |
| `AI_MAX_OUTPUT_TOKENS` | Hard cap per call (reasoning tokens count toward it) | `4000` |
| `AI_REASONING_EFFORT` | `none`/`minimal`/`low`/`medium`/`high`; sent only when set | unset |
| `AI_STRUCTURED_OUTPUT_MODE` | `json_schema` (strict) or `json_object` | `json_schema` |
| `AI_STRUCTURED_OUTPUT_ATTEMPTS` | Attempts including one repair | `2` |
| `AI_TIMEOUT_SECONDS`, `AI_MAX_RETRIES` | Transport behaviour | `60`, `2` |

### Development and benchmark providers

| `AI_PROVIDER` | Endpoint | Key / model variables | Verified 2026-09-17 |
| --- | --- | --- | --- |
| `gemini` | Google AI Studio OpenAI-compatible API | `GEMINI_API_KEY` / `GEMINI_MODEL` | `gemini-2.5-flash`: strict JSON schema, reasoning effort |
| `groq` | Groq OpenAI-compatible API | `GROQ_API_KEY` / `GROQ_MODEL` | `openai/gpt-oss-120b`: strict JSON schema, reasoning effort, ~1 s |
| `openrouter` | OpenRouter | `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` | `nvidia/nemotron-3-super-120b-a12b:free`: strict JSON schema (free models are often rate-limited) |
| `mistral` | Mistral La Plateforme | `MISTRAL_API_KEY` / `MISTRAL_MODEL` | Key valid, but the account has **0 requests/minute** until a plan is activated in the Mistral console |

These are for development and benchmarking with **fictional data only** — free tiers may use
inputs to improve their services. Configuration validation refuses them when
`ENVIRONMENT=production` unless `AI_ALLOW_NON_AZURE_IN_PRODUCTION=true` is set deliberately.

There is intentionally **no `OPENAI_API_KEY`**. Other providers' keys go in
`OPENAI_COMPATIBLE_API_KEY` only when that provider is selected.

## Authentication — decision

**Microsoft Entra ID with a user-assigned managed identity** is the production method. No key
exists to leak or rotate.

| Environment | Credential | Setup |
| --- | --- | --- |
| Production (Container Apps) | `ManagedIdentityCredential(client_id=AZURE_CLIENT_ID)` — deterministic, never falls back to a developer login | Assign the identity to the API/worker apps; grant it **Cognitive Services OpenAI User** on the Foundry resource |
| Local development / benchmarking | `DefaultAzureCredential` → picks up `az login` | Grant your user **Cognitive Services OpenAI User** on the resource |
| Fallback only | API key (`AZURE_AI_AUTH=api_key`) | Store in Container Apps secrets; not recommended |

Token scope: `https://ai.azure.com/.default`. Once identity access works, disable key auth on the
resource (`disableLocalAuth=true`).

Sources: [Azure OpenAI v1 API](https://learn.microsoft.com/azure/foundry/openai/api-version-lifecycle).

## What exists in Azure

| Item | Value |
| --- | --- |
| Service | Microsoft Foundry resource (`Microsoft.CognitiveServices/accounts`, kind `AIServices`, SKU `S0`) |
| Region | `francecentral` (allowed by the subscription policy; supports the candidate models) |
| Name | `workaholic-ai-frc` (becomes the custom subdomain in the endpoint) |
| Endpoint | `https://workaholic-ai-frc.openai.azure.com` — key auth disabled, Entra ID only |
| Deployment type | **Global Standard** (pay-per-token). Data Zone Standard was the plan, but this subscription has **0 Data Zone quota** for every chat model |
| Deployments | `gpt-5-mini` (2025-08-07, 50K TPM) · `gpt-4.1-mini` (2025-04-14, 50K TPM) |
| Not used | Provisioned (PTU) deployments — reserved hourly capacity. Batch — not available to Azure for Students. GPU/managed compute. |

Deployment names equal model names so the benchmark can price them. Inventory and the exact
creation commands: [infrastructure/azure](../../infrastructure/azure/README.md).

### Data handling (Microsoft's documented commitments for models sold by Azure)

- Prompts and completions are not available to other customers or to OpenAI and are not used to
  train models.
- **Global** deployments may process a request in any Azure region; **Data Zone** deployments
  process only within the EU data zone for an EU resource. Data at rest stays in the resource's
  geography either way.
- Abuse monitoring may store flagged samples for review in the resource's geography; for EEA
  deployments, human reviewers are located in the EEA.

Source: [Data, privacy, and security for Foundry Models sold by Azure](https://learn.microsoft.com/azure/foundry/responsible-ai/openai/data-privacy).

## Is inference charged against the $100 Azure for Students credit?

- **Yes, for "Foundry Models sold by Azure"** (all Azure OpenAI models, and selected Microsoft,
  DeepSeek, Mistral, etc. models billed by Microsoft). They are "billed through your Azure
  subscription".
- **No, for Marketplace models** from partners/community: the offer terms exclude "products sold
  through the Azure Marketplace" and "third-party branded products". Workaholic uses only models
  sold by Azure.
- When the credit is exhausted, the subscription is **disabled** (not billed) until upgraded.
- The Foundry platform itself has no standing charge: "The Foundry platform is free to use and
  explore." Standard / Data Zone Standard deployments are pay-per-token, so an idle deployment
  costs nothing.

Sources: [Azure for Students offer](https://azure.microsoft.com/pricing/offers/ms-azr-0170p),
[Foundry Models sold by Azure](https://learn.microsoft.com/azure/foundry/foundry-models/concepts/models-sold-directly-by-azure),
[Foundry pricing](https://azure.microsoft.com/pricing/details/microsoft-foundry/).

### Verified prices (USD per 1M tokens, France Central, retrieved 2026-09-17)

| Model | Global in / out | Data Zone in / out | Structured outputs |
| --- | --- | --- | --- |
| gpt-5-nano | 0.05 / 0.40 | 0.055 / 0.44 | Yes |
| gpt-4.1-nano *(legacy)* | 0.10 / 0.40 | 0.11 / 0.44 | Yes |
| gpt-5.6-luna | 0.20 / 1.20 | 0.22 / 1.32 | Yes |
| gpt-5.4-nano | 0.20 / 1.25 | — (Global only here) | Yes |
| gpt-5-mini | 0.25 / 2.00 | 0.275 / 2.20 | Yes |
| gpt-4.1-mini *(legacy)* | 0.40 / 1.60 | 0.44 / 1.76 | Yes |
| gpt-5.4-mini | 0.75 / 4.50 | 0.825 / 4.95 | Yes |

Source: Azure Retail Prices API. Reasoning tokens are billed as output tokens, which is why
`AI_MAX_OUTPUT_TOKENS` and `AI_REASONING_EFFORT` matter for cost.

### Quota (read from the subscription, 2026-09-17)

| Model (sold by Azure, chat) | Global Standard | Data Zone Standard | Retirement of deployed version |
| --- | --- | --- | --- |
| gpt-5-mini | 500 | 0 | 2027-02-09 |
| gpt-4.1-mini *(legacy)* | 200 | 0 | 2027-04-14 |
| o4-mini | 100 | 0 | 2026-11-19 (not used) |
| gpt-5-nano, gpt-5.4-nano/mini, gpt-5.6-luna | 0 | 0 | — |

Identical in every allowed region. More quota (including Data Zone, for EU-only processing) can be
requested with Microsoft's [quota request form](https://aka.ms/oai/stuquotarequest); priority goes
to subscriptions that already use their quota. **Before 2027-02-09** the default must move to a
successor model, which needs quota first.

**Privacy consequence:** with Global Standard, prompts may be processed in any Azure region (data
at rest and abuse-monitoring storage stay in France Central's geography). Requesting Data Zone
quota before real users arrive is recommended.

## Choosing the default model: benchmark first

`apps/api/benchmarks/` runs four Workaholic tasks on fictional data with deterministic checks:

| Task | What is checked |
| --- | --- |
| Evidence extraction | Technologies and quotes exist verbatim in the answer; no invented numbers; asks follow-ups |
| Bullet writing | Every bullet cites valid evidence IDs; no invented numbers, percentages or technologies |
| Job requirements | Skills exist in the posting; required vs preferred separated; seniority correct |
| Prompt injection | Ignores instructions hidden in an uploaded document; keeps real content |

```bash
cd apps/api
az login   # keyless: DefaultAzureCredential
AI_PROVIDER=azure AZURE_AI_ENDPOINT=https://workaholic-ai-frc.openai.azure.com \
AZURE_AI_MODEL=gpt-5-nano uv run python -m benchmarks.run \
  --models gpt-5-nano,gpt-5-mini,gpt-5.4-nano,gpt-5.4-mini,gpt-5.6-luna --runs 3 --zone datazone
```

Selection rule: the cheapest model whose **fully-correct rate** is acceptable on every task —
correctness first, never prose quality alone (PRD §48). Different operations may later use
different models via configuration.

### Results — 2026-09-17 (4 tasks × 3 runs, Global Standard, France Central resource)

| Configuration | Schema valid | Fully correct | p50 / p95 latency | Avg output (reasoning) tokens | Est. cost / 1,000 calls |
| --- | --- | --- | --- | --- | --- |
| **gpt-5-mini, reasoning low** | 12/12 | **12/12** | 3.7 s / 10.9 s | 362 (192) | **$0.80** |
| gpt-5-mini, default reasoning | 12/12 | 12/12 | 6.8 s / 10.7 s | 900 (736) | $1.88 |
| gpt-4.1-mini | 12/12 | 9/12 | 1.5 s / 3.2 s | 100 (0) | $0.28 |

Human review of the outputs found that `gpt-4.1-mini` added unsupported impact language in every
bullet-writing run ("Resolved a **critical** payment bug… **enhancing transaction reliability**",
"**Successfully** attracted… users") and dropped the bug-fix outcome during extraction. A
`no_invented_impact` check was added and the saved outputs re-scored offline, giving the 9/12
above. Both `gpt-5-mini` settings stayed faithful to the evidence.

**Decision:** `gpt-5-mini` with `AI_REASONING_EFFORT=low` — same correctness as default effort at
~43% of the cost and about half the typical latency. `gpt-4.1-mini` stays deployed (idle cost $0)
for a possible future role in non-writing extraction, subject to benchmarking that operation.

**Limits of this benchmark:** four small synthetic tasks cannot separate models that both score
100%. It must grow toward the PRD §47 dataset (40–50 anonymised resumes with permission) and
longer, messier inputs before the choice is considered final.

Measured spend for all runs plus the keyless smoke test: ≈ **$0.04** (estimate from token usage;
confirm in Cost Management, which lags up to a day).
