"""Access-token verification. Identity must only ever come from a valid, verified token."""

import asyncio
import time
import uuid
from typing import Any

import httpx
import jwt
import pytest

from app.services.auth import supabase as supabase_auth
from tests.conftest import AppFactory, FakeIdentityProvider, SigningKey, bearer, running

ME = "/api/v1/me"


def assert_rejected(response: httpx.Response, code: str = "UNAUTHENTICATED") -> None:
    assert response.status_code == 401
    assert response.json()["error"]["code"] == code
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_valid_token_is_accepted(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    response = await client.get(ME, headers=bearer(idp.token()))

    assert response.status_code == 200


async def test_missing_token_is_rejected(client: httpx.AsyncClient) -> None:
    assert_rejected(await client.get(ME))


async def test_non_bearer_scheme_is_rejected(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    assert_rejected(await client.get(ME, headers={"Authorization": f"Basic {idp.token()}"}))


@pytest.mark.parametrize("garbage", ["not-a-jwt", "a.b.c", "eyJhbGciOiJFUzI1NiJ9.e30.sig"])
async def test_malformed_token_is_rejected(client: httpx.AsyncClient, garbage: str) -> None:
    assert_rejected(await client.get(ME, headers=bearer(garbage)))


async def test_expired_token_reports_session_expired(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    token = idp.token(expires_in=-120, iat=int(time.time()) - 3720)

    assert_rejected(await client.get(ME, headers=bearer(token)), code="SESSION_EXPIRED")


@pytest.mark.parametrize(
    "claims",
    [
        {"aud": "some-other-audience"},
        {"iss": "https://attacker.supabase.co/auth/v1"},
        {"role": "anon"},
        {"role": "service_role"},
        {"is_anonymous": True},
        {"sub": ...},
        {"exp": ...},
    ],
    ids=[
        "wrong-audience",
        "wrong-issuer",
        "anon-role",
        "service-role",
        "anonymous",
        "no-sub",
        "no-exp",
    ],
)
async def test_token_with_invalid_claims_is_rejected(
    client: httpx.AsyncClient, idp: FakeIdentityProvider, claims: dict[str, Any]
) -> None:
    assert_rejected(await client.get(ME, headers=bearer(idp.token(**claims))))


async def test_token_signed_by_unknown_private_key_is_rejected(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    impostor = SigningKey(kid=idp.keys[0].kid)  # same key ID, different private key

    assert_rejected(await client.get(ME, headers=bearer(idp.token(key=impostor))))


async def test_symmetric_hs256_token_is_rejected(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    # A token forged with a shared secret (e.g. a leaked legacy JWT secret) must never pass.
    claims = jwt.decode(idp.token(), options={"verify_signature": False})
    forged = jwt.encode(
        claims,
        "legacy-shared-secret-value-32-bytes!",
        algorithm="HS256",
        headers={"kid": idp.keys[0].kid},
    )

    assert_rejected(await client.get(ME, headers=bearer(forged)))


async def test_unsigned_alg_none_token_is_rejected(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    claims = jwt.decode(idp.token(), options={"verify_signature": False})
    unsigned = jwt.encode(claims, "", algorithm="none", headers={"kid": idp.keys[0].kid})

    assert_rejected(await client.get(ME, headers=bearer(unsigned)))


async def test_identity_is_never_taken_from_the_request(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    subject = str(uuid.uuid4())
    token = idp.token(subject, email="real@example.com")

    response = await client.get(
        f"{ME}?user_id=someone-else",
        headers={**bearer(token), "X-User-Id": "someone-else"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "real@example.com"


async def test_unknown_key_ids_do_not_trigger_unbounded_key_fetches(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    await client.get(ME, headers=bearer(idp.token()))
    assert idp.jwks_requests == 1

    for index in range(5):
        stranger = SigningKey(kid=f"made-up-{index}")
        assert_rejected(await client.get(ME, headers=bearer(idp.token(key=stranger))))

    assert idp.jwks_requests == 1


async def test_rotated_signing_key_is_picked_up(
    client: httpx.AsyncClient, idp: FakeIdentityProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    await client.get(ME, headers=bearer(idp.token()))
    monkeypatch.setattr(supabase_auth, "MIN_REFETCH_INTERVAL_SECONDS", 0.0)

    new_key = SigningKey(kid="key-2")
    idp.keys.append(new_key)
    response = await client.get(ME, headers=bearer(idp.token(key=new_key)))

    assert response.status_code == 200
    assert idp.jwks_requests == 2


async def test_identity_provider_outage_is_reported_as_unavailable(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    idp.available = False

    response = await client.get(ME, headers=bearer(idp.token()))

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "AUTH_PROVIDER_UNAVAILABLE"


@pytest.mark.usefixtures("db_engine")
async def test_cached_keys_survive_identity_provider_outage(
    make_app: AppFactory, idp: FakeIdentityProvider, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Keys go stale immediately, so every request below tries (and fails) to refetch them.
    monkeypatch.setattr(supabase_auth, "MIN_REFETCH_INTERVAL_SECONDS", 0.0)
    async with running(make_app(jwks_cache_ttl_seconds=0)) as client:
        assert (await client.get(ME, headers=bearer(idp.token()))).status_code == 200
        idp.available = False

        responses = await asyncio.gather(
            *(client.get(ME, headers=bearer(idp.token())) for _ in range(3))
        )

    assert [response.status_code for response in responses] == [200, 200, 200]
    assert idp.jwks_requests > 1
