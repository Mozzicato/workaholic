"""Supabase Auth token verification.

Access tokens are verified locally against the project's published public keys (JWKS).
Only asymmetric algorithms are accepted, so no shared secret exists on this server and a
token cannot be forged with the legacy HS256 secret or `alg: none`.
"""

import asyncio
import time
from typing import Any

import httpx
import jwt
import structlog

from app.core.config import Settings
from app.core.errors import AuthProviderUnavailableError, SessionExpiredError, UnauthenticatedError
from app.services.auth.base import AuthenticatedPrincipal

logger = structlog.get_logger(__name__)

ALLOWED_ALGORITHMS = frozenset({"ES256", "RS256"})
# Minimum gap between key fetches once keys are cached, so tokens with made-up key IDs
# cannot be used to hammer the identity provider.
MIN_REFETCH_INTERVAL_SECONDS = 30.0
_CLOCK_SKEW_LEEWAY_SECONDS = 30


class JwksCache:
    def __init__(self, url: str, http: httpx.AsyncClient, ttl_seconds: int) -> None:
        self._url = url
        self._http = http
        self._ttl = ttl_seconds
        self._keys: dict[str, jwt.PyJWK] = {}
        self._fetched_at = float("-inf")  # last successful fetch
        self._attempted_at = float("-inf")  # last fetch attempt, successful or not
        self._lock = asyncio.Lock()

    async def get_key(self, kid: str) -> jwt.PyJWK | None:
        if time.monotonic() - self._fetched_at > self._ttl:
            await self._refresh()
        if kid not in self._keys:
            # The provider may have rotated keys since the last fetch.
            await self._refresh()
        return self._keys.get(kid)

    async def _refresh(self) -> None:
        async with self._lock:
            recently_attempted = (
                time.monotonic() - self._attempted_at < MIN_REFETCH_INTERVAL_SECONDS
            )
            if self._keys and recently_attempted:
                return
            self._attempted_at = time.monotonic()
            try:
                response = await self._http.get(self._url, timeout=5.0)
                response.raise_for_status()
                jwk_set = jwt.PyJWKSet.from_dict(response.json())
            except (httpx.HTTPError, ValueError, jwt.PyJWKSetError) as exc:
                logger.warning("jwks_fetch_failed", error_type=type(exc).__name__)
                if not self._keys:
                    raise AuthProviderUnavailableError() from exc
                return  # keep serving the last known keys rather than failing every request
            self._keys = {key.key_id: key for key in jwk_set.keys if key.key_id}
            self._fetched_at = time.monotonic()


class SupabaseAuthProvider:
    def __init__(
        self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._issuer = settings.supabase_issuer
        self._audience = settings.supabase_jwt_audience
        self._http = httpx.AsyncClient(transport=transport)
        self._jwks = JwksCache(
            settings.supabase_jwks_url, self._http, settings.jwks_cache_ttl_seconds
        )

    async def verify_access_token(self, token: str) -> AuthenticatedPrincipal:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise UnauthenticatedError() from exc

        algorithm = header.get("alg")
        kid = header.get("kid")
        if algorithm not in ALLOWED_ALGORITHMS or not isinstance(kid, str):
            raise UnauthenticatedError()

        signing_key = await self._jwks.get_key(kid)
        if signing_key is None:
            raise UnauthenticatedError()

        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                key=signing_key,
                algorithms=[algorithm],
                audience=self._audience,
                issuer=self._issuer,
                leeway=_CLOCK_SKEW_LEEWAY_SECONDS,
                options={"require": ["exp", "iat", "sub", "aud", "iss"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise SessionExpiredError() from exc
        except jwt.InvalidTokenError as exc:
            raise UnauthenticatedError() from exc

        if claims.get("role") != "authenticated" or claims.get("is_anonymous") is True:
            raise UnauthenticatedError()

        return _principal_from_claims(claims)

    async def aclose(self) -> None:
        await self._http.aclose()


def _principal_from_claims(claims: dict[str, Any]) -> AuthenticatedPrincipal:
    app_metadata = claims.get("app_metadata") or {}
    user_metadata = claims.get("user_metadata") or {}
    name = user_metadata.get("full_name") or user_metadata.get("name")
    email = claims.get("email")
    return AuthenticatedPrincipal(
        subject=str(claims["sub"]),
        provider=str(app_metadata.get("provider") or "email"),
        email=email if isinstance(email, str) and email else None,
        name=name.strip()[:200] if isinstance(name, str) and name.strip() else None,
    )
