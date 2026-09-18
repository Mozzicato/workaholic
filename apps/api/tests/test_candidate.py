"""Candidate profile, evidence and resumes: ownership, validation and evidence rules."""

import uuid
from typing import Any

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import EvidenceStatus
from app.models.user import User
from app.services.candidate import EvidenceService
from tests.conftest import FakeIdentityProvider, bearer

PROFILE = "/api/v1/profile"
EVIDENCE = "/api/v1/evidence"
RESUMES = "/api/v1/resumes"


def experience_item(**overrides: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "employer": "Lumen Freight",
        "title": "Backend Engineer Intern",
        "start_date": "2025-06",
        "end_date": "2025-09",
        "bullets": ["Built an internal API with FastAPI"],
        "technologies": ["Python", "FastAPI"],
    }
    item.update(overrides)
    return item


# ── Profile ──────────────────────────────────────────────────────────────────


async def test_profile_is_created_empty_on_first_read(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    response = await client.get(PROFILE, headers=bearer(idp.token()))

    assert response.status_code == 200
    profile = response.json()
    assert profile["experience"] == []
    assert profile["basics"] == {
        "full_name": None,
        "headline": None,
        "email": None,
        "phone": None,
        "location": None,
        "summary": None,
    }


async def test_sections_update_independently(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    token = bearer(idp.token(str(uuid.uuid4())))
    await client.patch(PROFILE, headers=token, json={"basics": {"full_name": "Ada Lovelace"}})

    response = await client.patch(PROFILE, headers=token, json={"experience": [experience_item()]})

    profile = response.json()
    assert response.status_code == 200
    assert profile["basics"]["full_name"] == "Ada Lovelace"  # untouched by the second call
    assert profile["experience"][0]["employer"] == "Lumen Freight"
    assert uuid.UUID(profile["experience"][0]["id"])  # server-assigned, stable for evidence


async def test_replacing_a_section_removes_items_left_out(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    token = bearer(idp.token(str(uuid.uuid4())))
    await client.patch(
        PROFILE,
        headers=token,
        json={"skills": [{"name": "Python"}, {"name": "FastAPI"}]},
    )

    response = await client.patch(PROFILE, headers=token, json={"skills": [{"name": "Python"}]})

    assert [skill["name"] for skill in response.json()["skills"]] == ["Python"]


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        ({"experience": [experience_item(start_date="June 2025")]}, "date format"),
        ({"experience": [experience_item(start_date="2025-09", end_date="2025-06")]}, "date order"),
        ({"basics": {"full_name": "Ada", "nickname": "Addy"}}, "unknown field"),
        ({"links": {"website": "not-a-url"}}, "invalid url"),
        ({"skills": [{"name": ""}]}, "empty name"),
        ({"skills": [{"name": "x"}] * 200}, "too many items"),
    ],
)
async def test_invalid_profile_content_is_rejected(
    client: httpx.AsyncClient, idp: FakeIdentityProvider, payload: dict[str, Any], reason: str
) -> None:
    response = await client.patch(PROFILE, headers=bearer(idp.token()), json=payload)

    assert response.status_code == 422, reason
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_each_user_has_their_own_profile(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    await client.patch(
        PROFILE, headers=bearer(idp.token("user-a")), json={"basics": {"full_name": "Ada"}}
    )

    response = await client.get(PROFILE, headers=bearer(idp.token("user-b")))

    assert response.json()["basics"]["full_name"] is None


# ── Evidence ─────────────────────────────────────────────────────────────────


async def test_user_statements_are_factual_immediately(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    response = await client.post(
        EVIDENCE,
        headers=bearer(idp.token()),
        json={
            "claim": "Built a textbook swap site used by about 300 students",
            "section": "projects",
        },
    )

    assert response.status_code == 201
    evidence = response.json()
    assert evidence["status"] == EvidenceStatus.USER_PROVIDED
    assert evidence["source"] == "user_input"
    assert evidence["confirmed_at"] is not None


async def test_model_suggestions_are_not_factual_until_confirmed(
    client: httpx.AsyncClient, idp: FakeIdentityProvider, session: AsyncSession
) -> None:
    subject = str(uuid.uuid4())
    token = bearer(idp.token(subject))
    await client.get(PROFILE, headers=token)  # provisions the user and profile
    user = (await session.execute(select(User).where(User.auth_subject == subject))).scalar_one()

    proposed = await EvidenceService(session).record_model_inference(
        user, "Led a team of five engineers"
    )

    listed = (await client.get(f"{EVIDENCE}?status=MODEL_INFERRED", headers=token)).json()
    assert [item["claim"] for item in listed] == ["Led a team of five engineers"]
    assert listed[0]["confirmed_at"] is None

    confirmed = (await client.post(f"{EVIDENCE}/{proposed.id}/confirm", headers=token)).json()
    assert confirmed["status"] == EvidenceStatus.USER_CONFIRMED
    assert confirmed["confirmed_at"] is not None


async def test_evidence_can_be_deleted_by_its_owner(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    token = bearer(idp.token(str(uuid.uuid4())))
    created = (
        await client.post(EVIDENCE, headers=token, json={"claim": "Shipped a feature"})
    ).json()

    assert (await client.delete(f"{EVIDENCE}/{created['id']}", headers=token)).status_code == 204
    assert (await client.get(EVIDENCE, headers=token)).json() == []


# ── Resumes ──────────────────────────────────────────────────────────────────


async def test_resume_starts_as_an_empty_draft(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    response = await client.post(
        RESUMES,
        headers=bearer(idp.token()),
        json={"title": "Backend Engineer", "target_role": "Junior Backend Engineer"},
    )

    assert response.status_code == 201
    resume = response.json()
    assert (resume["status"], resume["document_type"]) == ("draft", "resume")
    assert resume["current_version_id"] is None  # nothing is generated yet


async def test_resume_titles_are_unique_per_user(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    token = bearer(idp.token(str(uuid.uuid4())))
    await client.post(RESUMES, headers=token, json={"title": "Backend Engineer"})

    duplicate = await client.post(RESUMES, headers=token, json={"title": "Backend Engineer"})

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "CONFLICT"
    # The same title is fine for a different person.
    other = await client.post(
        RESUMES, headers=bearer(idp.token(str(uuid.uuid4()))), json={"title": "Backend Engineer"}
    )
    assert other.status_code == 201


async def test_resumes_can_be_renamed_and_deleted(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    token = bearer(idp.token(str(uuid.uuid4())))
    created = (await client.post(RESUMES, headers=token, json={"title": "Draft"})).json()

    renamed = await client.patch(
        f"{RESUMES}/{created['id']}", headers=token, json={"title": "Data Science Resume"}
    )
    assert renamed.json()["title"] == "Data Science Resume"
    assert renamed.json()["target_role"] is None

    assert (await client.delete(f"{RESUMES}/{created['id']}", headers=token)).status_code == 204
    assert (await client.get(f"{RESUMES}/{created['id']}", headers=token)).status_code == 404


async def test_listing_shows_only_your_own_resumes(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    await client.post(RESUMES, headers=bearer(idp.token("owner")), json={"title": "Mine"})

    listed = await client.get(RESUMES, headers=bearer(idp.token("stranger")))

    assert listed.json() == []


# ── Authorization (IDOR) ─────────────────────────────────────────────────────


async def test_one_user_cannot_touch_another_users_records(
    client: httpx.AsyncClient, idp: FakeIdentityProvider
) -> None:
    owner = bearer(idp.token("owner-subject"))
    attacker = bearer(idp.token("attacker-subject"))
    resume = (await client.post(RESUMES, headers=owner, json={"title": "Private"})).json()
    evidence = (await client.post(EVIDENCE, headers=owner, json={"claim": "Confidential"})).json()

    attempts = {
        "read resume": await client.get(f"{RESUMES}/{resume['id']}", headers=attacker),
        "rename resume": await client.patch(
            f"{RESUMES}/{resume['id']}", headers=attacker, json={"title": "Stolen"}
        ),
        "delete resume": await client.delete(f"{RESUMES}/{resume['id']}", headers=attacker),
        "confirm evidence": await client.post(
            f"{EVIDENCE}/{evidence['id']}/confirm", headers=attacker
        ),
        "delete evidence": await client.delete(f"{EVIDENCE}/{evidence['id']}", headers=attacker),
    }

    assert {name: r.status_code for name, r in attempts.items()} == dict.fromkeys(attempts, 404)
    # The owner's records are untouched.
    assert (await client.get(f"{RESUMES}/{resume['id']}", headers=owner)).json()[
        "title"
    ] == "Private"
    assert len((await client.get(EVIDENCE, headers=owner)).json()) == 1


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", PROFILE),
        ("PATCH", PROFILE),
        ("GET", EVIDENCE),
        ("POST", EVIDENCE),
        ("GET", RESUMES),
        ("POST", RESUMES),
    ],
)
async def test_every_endpoint_requires_authentication(
    client: httpx.AsyncClient, method: str, path: str
) -> None:
    response = await client.request(method, path, json={})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


@pytest.mark.usefixtures("db_engine")
class TestItemIdentityIsStable:
    """Evidence points at profile items by id, so an id that changes breaks the whole chain."""

    async def test_an_item_keeps_its_id_across_reads(
        self, client: httpx.AsyncClient, idp: FakeIdentityProvider
    ) -> None:
        headers = bearer(idp.token(subject=str(uuid.uuid4()), email="ada@example.com"))
        await client.get("/api/v1/me", headers=headers)
        await client.patch(
            PROFILE,
            headers=headers,
            json={"skills": [{"name": "Python"}], "experience": [experience_item()]},
        )

        first = (await client.get(PROFILE, headers=headers)).json()
        second = (await client.get(PROFILE, headers=headers)).json()

        assert first["skills"][0]["id"] == second["skills"][0]["id"]
        assert first["experience"][0]["id"] == second["experience"][0]["id"]

    async def test_an_id_the_user_supplies_is_kept(
        self, client: httpx.AsyncClient, idp: FakeIdentityProvider
    ) -> None:
        headers = bearer(idp.token(subject=str(uuid.uuid4()), email="ada@example.com"))
        await client.get("/api/v1/me", headers=headers)

        await client.patch(
            PROFILE, headers=headers, json={"skills": [{"id": "skill-1", "name": "Python"}]}
        )
        stored = (await client.get(PROFILE, headers=headers)).json()

        assert stored["skills"][0]["id"] == "skill-1"

    async def test_updating_one_section_leaves_another_section_s_ids_alone(
        self, client: httpx.AsyncClient, idp: FakeIdentityProvider
    ) -> None:
        headers = bearer(idp.token(subject=str(uuid.uuid4()), email="ada@example.com"))
        await client.get("/api/v1/me", headers=headers)
        await client.patch(
            PROFILE,
            headers=headers,
            json={"skills": [{"name": "Python"}], "experience": [experience_item()]},
        )
        before = (await client.get(PROFILE, headers=headers)).json()

        await client.patch(PROFILE, headers=headers, json={"skills": [{"name": "Python"}]})
        after = (await client.get(PROFILE, headers=headers)).json()

        assert before["experience"][0]["id"] == after["experience"][0]["id"]
