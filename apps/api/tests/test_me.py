"""Account provisioning: a verified identity maps to exactly one Workaholic user."""

import asyncio
import uuid

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.models.user import User
from tests.conftest import AppFactory, FakeIdentityProvider, bearer, running

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
    assert set(body) == {
        "id",
        "email",
        "name",
        "auth_provider",
        "created_at",
        "is_admin",
        "tour_seen",
    }
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


@pytest.mark.usefixtures("db_engine")
async def test_an_account_can_erase_itself(make_app: AppFactory, idp: FakeIdentityProvider) -> None:
    """Leaving must be possible, and must take everything with it."""
    async with running(make_app()) as client:
        headers = bearer(idp.token(subject="user-leaving", email="ada@example.com"))
        await client.get(ME, headers=headers)
        await client.patch(
            "/api/v1/profile", headers=headers, json={"skills": [{"name": "Python"}]}
        )
        await client.post("/api/v1/resumes", headers=headers, json={"title": "Mine"})

        deleted = await client.delete(ME, headers=headers)

        # The same person signing in again gets an empty account, not their old one.
        again = await client.get(ME, headers=headers)
        profile = await client.get("/api/v1/profile", headers=headers)
        resumes = await client.get("/api/v1/resumes", headers=headers)

    assert deleted.status_code == 204
    assert again.status_code == 200
    assert profile.json()["skills"] == []
    assert resumes.json() == []


@pytest.mark.usefixtures("db_engine")
async def test_the_walkthrough_is_remembered_per_account_not_per_browser(
    make_app: AppFactory, idp: FakeIdentityProvider
) -> None:
    """Seen on a laptop is seen on a phone: it is the person who has been shown, not the device."""
    async with running(make_app()) as client:
        headers = bearer(idp.token(subject="user-new", email="ada@example.com"))

        first = await client.get(ME, headers=headers)
        marked = await client.post(f"{ME}/tour", headers=headers)
        again = await client.get(ME, headers=headers)

    assert first.json()["tour_seen"] is False
    assert marked.status_code == 200
    assert marked.json()["tour_seen"] is True
    assert again.json()["tour_seen"] is True


@pytest.mark.usefixtures("db_engine")
async def test_the_walkthrough_cannot_be_marked_seen_for_somebody_else(
    make_app: AppFactory,
) -> None:
    async with running(make_app()) as client:
        response = await client.post(f"{ME}/tour")

    assert response.status_code == 401
