# ADR-007 — Voice is an interface over the interview, and the transcript is not the record

**Status:** Accepted · 2026-09-18

## Context

PRD §26 makes voice an interface over the interview agent, not a second reasoning system, and
§27 requires a provider abstraction and forbids storing raw audio by default.

There is a subtler risk than storage. Speech recognition mishears proper nouns — the exact class
of word a resume is built from. "Lumen Freight" becomes "loomin freight"; a company called Vertex
becomes "vertices". If a transcript were written straight into the career record, the product
would be putting words into someone's mouth by accident, which is the same failure as inventing
them on purpose, only harder to notice.

## Decision

1. **Speech goes through `SpeechToTextProvider`.** Application code receives text; which service
   produced it is configuration. Azure and Groq both speak the OpenAI audio API, so one
   implementation covers them and anything else that follows that shape.
2. **The default is `gpt-4o-transcribe` on the existing Foundry resource**, under the same managed
   identity as the chat models. No new Azure resource, no standing charge, and the person's spoken
   career history stays inside Azure.
3. **A transcript lands in the answer box, never in the record.** The person reads it, corrects
   what was misheard, and presses send. What is stored is what they approved.
4. **Audio is never persisted.** It is held in memory for one request and discarded. Only lengths
   and latencies are logged, never content.
5. **Ownership is checked before any audio leaves the process**, so an interview id that is not
   yours cannot be used to send audio anywhere.
6. **Typing always works.** The microphone hides itself where the browser cannot record, the API
   answers 503 with "you can type your answer instead" when speech is off or failing, and no part
   of the interview depends on voice.

## Consequences

- Voice is slower than speaking to a real-time agent: record, stop, read, send. PRD §26 asks for
  reliability over conversational theatrics at this stage, and reading the transcript back is the
  step that keeps the record honest.
- Cost is proportional to speech, about $0.22 per hour, and zero when nobody is talking.
- Audio transcription is **not** served by the Azure OpenAI v1 API that the chat models use: that
  path answers `DeploymentNotFound` even for a healthy deployment. Only the deployment-scoped path
  with a dated `api-version` works, which is why speech uses `AsyncAzureOpenAI` while chat does
  not. Verified against the live resource on 2026-09-18.
- Because the transcript is editable text rather than a committed answer, the injection defences
  from ADR-005 and ADR-006 apply to it unchanged: a spoken instruction is refused exactly as a
  typed one is.
