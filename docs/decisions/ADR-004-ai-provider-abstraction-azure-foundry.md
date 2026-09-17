# ADR-004 — AI provider abstraction with Azure Foundry as the primary provider

**Status:** Accepted · 2026-09-17

## Context

Workaholic needs LLM inference for interviews, extraction, writing, tailoring and qualitative ATS
feedback. The project runs on an Azure for Students subscription, the PRD requires a provider
abstraction with configuration-driven model selection (§28, §57), and model choice must be based
on benchmarks rather than impressions (§48). A third-party gateway was evaluated and rejected: it
only accepts whitelisted coding tools and its terms prohibit bypassing that restriction.

## Decision

1. Application code depends on an `LLMProvider` protocol (`generate`, `structured_output`,
   `stream`), never on a vendor SDK.
2. The primary implementation calls **Azure Foundry models sold by Azure** through the Azure
   OpenAI **v1 API** using the standard `openai` SDK.
3. Authentication is **Microsoft Entra ID**: a user-assigned managed identity in production
   (`ManagedIdentityCredential`), `DefaultAzureCredential` (`az login`) in development. API keys
   are supported only as an explicit fallback.
4. Inference uses **Chat Completions** (stateless) rather than the Responses API, which stores
   conversation state at rest.
5. Deployments use **Data Zone Standard** (EU processing) where available, else Global Standard.
   No provisioned throughput, no managed compute, no GPUs.
6. Other providers (Groq, Gemini, Mistral, NVIDIA NIM, Hugging Face, OpenAI) plug in through a
   single OpenAI-compatible adapter; providers with other protocols add a class implementing the
   same protocol.
7. The default model is chosen from benchmark results (`apps/api/benchmarks`) using deterministic
   fabrication and injection checks, cheapest acceptable model first.

## Consequences

- No AI secret exists in production; access is revoked by removing a role assignment.
- Inference is billed per token against the Azure credit; idle deployments cost nothing.
- Marketplace models are excluded because the student credit does not cover them.
- Responses-API-only features (hosted tools, stored conversations) are unavailable by choice.
- Details: [AI platform](../architecture/ai-platform.md), [Azure cost plan](../architecture/azure-cost-plan.md).
