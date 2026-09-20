"""Account provisioning: a verified identity maps to exactly one Workaholic user."""

import asyncio
import uuid

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.user import User
from tests.conftest import FakeIdentityProvider, bearer

ME = "/api/v1/me"


async def count_users(engine: AsyncEngine) -> int:
    async with engine.connect() as connection:
        return (await connection.execute(select(func.count()).select_from(User))).scalar_one()


async def test_first_sign_in_creates_account(
    client: httpx.AsyncClient, idp: FakeIdentityProvider, db_engine: AsyncEngine
) -> None:
    token = idp.token(email="ada@example.com")

    response = await client.get(ME, headers=bearer(token))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"id", "email", "name", "auth_provider", "created_at", "is_admin"}
    assert body["email"] == "ada@example.com"
    assert body["auth_provider"] == "email"
    assert body["name"] is None
    assert await count_users(db_engine) == 1


async def test_repeat_requests_reuse_the_same_account(
    client: httpx.AsyncClient, idp: FakeIdentityProvider, db_engine: AsyncEngine
) -> None:
    subject = str(uuid.uuid4())

    first = await client.get(ME, headers=bearer(idp.token(subject)))
    second = await client.get(ME, headers=bearer(idp.token(subject)))

    assert first.json()["id"] == second.json()["id"]
    assert await count_users(db_engine) == 1


async def test_concurrent_first_requests_create_one_account(
    client: httpx.AsyncClient, idp: FakeIdentityProvider, db_engine: AsyncEngine
) -> None:
    token = idp.token(str(uuid.uuid4()))

    responses = await asyncio.gather(*(client.get(ME, headers=bearer(token)) for _ in range(8)))

    assert {response.status_code for response in responses} == {200}
    assert len({response.json()["id"] for response in responses}) == 1
    assert await count_users(db_engine) == 1


async def test_different_identities_get_separate_accounts(
    client: httpx.AsyncClient, idp: FakeIdentityProvider, db_engine: AsyncEngine
) -> None:
    ada = await client.get(ME, headers=bearer(idp.token(email="ada@example.com")))
    grace = await client.get(ME, headers=bearer(idp.token(email="grace@example.com")))

    assert ada.json()["id"] != grace.json()["id"]
    assert ada.json()["email"] == "ada@example.com"
    assert grace.json()["email"] == "grace@example.com"
    assert await count_users(db_engine) == 2


async def test_email_change_at_identity_provider_is_synced(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    subject = str(uuid.uuid4())
    await client.get(ME, headers=bearer(idp.token(subject, email="old@example.com")))

    response = await client.get(ME, headers=bearer(idp.token(subject, email="new@example.com")))

    assert response.json()["email"] == "new@example.com"


async def test_google_sign_in_records_provider_and_name(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    token = idp.token(
        app_metadata={"provider": "google", "providers": ["google"]},
        user_metadata={"full_name": "  Ada Lovelace  ", "avatar_url": "https://example.com/a.png"},
    )

    body = (await client.get(ME, headers=bearer(token))).json()

    assert body["auth_provider"] == "google"
    assert body["name"] == "Ada Lovelace"
