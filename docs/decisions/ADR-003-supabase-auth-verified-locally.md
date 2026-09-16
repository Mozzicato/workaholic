# ADR-003 — Supabase Auth, verified locally with asymmetric keys

**Status:** Accepted · 2026-09-16

## Context

Supabase provides authentication only; application data lives in Azure PostgreSQL. The API
must derive identity solely from a verified token and must remain replaceable behind an
interface.

## Decision

- The web app signs users in with Supabase (`@supabase/ssr`, PKCE flow) and sends the
  access token to the API as a Bearer token.
- The API verifies tokens locally against the project's JWKS
  (`/auth/v1/.well-known/jwks.json`). Only `ES256`/`RS256` are accepted, so `HS256`
  (legacy shared secret) and `alg: none` tokens are rejected outright. Audience, issuer,
  expiry, `role = authenticated` and non-anonymous sessions are enforced.
- Keys are cached (10 minutes) with rate-limited refetch on unknown key IDs, and the last
  known keys keep working during a Supabase outage.
- The API maps the provider's user ID (`sub`) to an internal `users.id`. Every user-owned
  row references the internal ID, never the provider ID.
- The legacy `anon` / `service_role` keys are not used; the publishable key is used in the
  browser and the secret key only on the server.

## Consequences

- No JWT secret is stored anywhere in Workaholic.
- A signed-out session remains valid at the API until its access token expires (≈1 hour).
  Acceptable for V1; revisit if immediate revocation becomes a requirement.
- Supabase free projects pause after a week of low activity. Before launch: upgrade or add
  a keep-alive.
