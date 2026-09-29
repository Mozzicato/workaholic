"""Tailoring and the ATS score, through the API.

The unit tests prove the rules; these prove the endpoints apply them to the right document, for
the right person, and keep a tailored copy as a new version rather than overwriting the old one.
"""

import uuid
from typing import Any

import pytest

from tests.conftest import AppFactory, FakeIdentityProvider, bearer, running
from tests.test_jobs import ADVERT, ANALYSIS
from tests.test_resume_generation import PROFILE, ScriptedLLM, app_with, set_up_record, sign_in

RESUMES = "/api/v1/resumes"

TWO_ROLE_PROFILE: dict[str, Any] = {
    **PROFILE,
    "experience": [
        {
            "employer": "Campus Cafe",
            "title": "Barista",
            "start_date": "2024-01",
            "bullets": ["served customers during the morning rush"],
            "technologies": [],
        },
        *PROFILE["experience"],
    ],
}

WORDING = {
    "summary": "",
    "bullets": [
        {"source_ids": ["e0.b0"], "text": "Served customers during the morning rush"},
        {"source_ids": ["e1.b0"], "text": "Helped build the payouts reconciliation service"},
    ],
}


async def generated(client: Any, headers: dict[str, str]) -> tuple[str, str]:
    resume_id = await set_up_record(client, headers, profile=TWO_ROLE_PROFILE)
    version = await client.post(f"{RESUMES}/{resume_id}/versions", headers=headers, json={})
    assert version.status_code == 201, version.text
    return resume_id, version.json()["id"]


async def job(client: Any, headers: dict[str, str]) -> str:
    created = await client.post(
        "/api/v1/jobs", headers=headers, json={"title": "Junior Backend", "raw_text": ADVERT}
    )
    identifier: str = created.json()["id"]
    return identifier


@pytest.mark.usefixtures("db_engine")
class TestTailoring:
    async def test_tailoring_keeps_the_original_and_adds_a_version(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(WORDING, ANALYSIS)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            resume_id, version_id = await generated(client, headers)
            job_id = await job(client, headers)

            tailored = await client.post(
                f"{RESUMES}/{resume_id}/versions/{version_id}/tailored",
                headers=headers,
                json={"job_id": job_id},
            )
            versions = await client.get(f"{RESUMES}/{resume_id}/versions", headers=headers)

        assert tailored.status_code == 201
        assert [v["version_number"] for v in versions.json()] == [2, 1]
        roles = tailored.json()["version"]["content"]["experience"]
        assert roles[0]["employer"] == "Paystack", "the role that matches the job leads"

    async def test_the_summary_explains_what_moved_and_what_is_missing(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(WORDING, ANALYSIS)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            resume_id, version_id = await generated(client, headers)
            job_id = await job(client, headers)

            tailored = await client.post(
                f"{RESUMES}/{resume_id}/versions/{version_id}/tailored",
                headers=headers,
                json={"job_id": job_id},
            )

        summary = tailored.json()["summary"]
        assert summary["changed"]
        assert any("employers" in line.lower() for line in summary["unchanged"])
        assert "AWS" in summary["missing_requirements"]

    async def test_tailoring_never_adds_the_missing_requirements(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(WORDING, ANALYSIS)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            resume_id, version_id = await generated(client, headers)
            job_id = await job(client, headers)

            tailored = await client.post(
                f"{RESUMES}/{resume_id}/versions/{version_id}/tailored",
                headers=headers,
                json={"job_id": job_id},
            )

        content = str(tailored.json()["version"]["content"]).lower()
        assert "aws" not in content
        assert "docker" not in content

    async def test_another_account_s_job_cannot_be_used(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(WORDING, ANALYSIS)
        async with running(app_with(llm, make_app)) as client:
            owner = await sign_in(client, idp)
            resume_id, version_id = await generated(client, owner)

            other = bearer(idp.token(subject=str(uuid.uuid4()), email="eve@example.com"))
            await client.get("/api/v1/me", headers=other)
            their_job = await job(client, other)

            response = await client.post(
                f"{RESUMES}/{resume_id}/versions/{version_id}/tailored",
                headers=owner,
                json={"job_id": their_job},
            )

        assert response.status_code == 404


@pytest.mark.usefixtures("db_engine")
class TestAtsScore:
    async def test_a_version_gets_a_scored_explained_report(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(WORDING)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            resume_id, version_id = await generated(client, headers)

            report = await client.get(
                f"{RESUMES}/{resume_id}/versions/{version_id}/ats", headers=headers
            )

        assert report.status_code == 200
        body = report.json()
        assert body["maximum"] == 100
        assert 0 <= body["score"] <= 100
        assert len(body["categories"]) == 5
        assert "Workaholic ATS Compatibility Score" in body["caveat"]
        assert all(check["detail"] for check in body["checks"])

    async def test_attaching_a_job_checks_its_keywords(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(WORDING, ANALYSIS)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            resume_id, version_id = await generated(client, headers)
            job_id = await job(client, headers)

            report = await client.get(
                f"{RESUMES}/{resume_id}/versions/{version_id}/ats",
                headers=headers,
                params={"job_id": job_id},
            )

        checks = {check["name"]: check for check in report.json()["checks"]}
        assert "Required skills present" in checks
        assert "No job attached" not in checks["Keyword coverage"]["detail"]

    async def test_another_account_cannot_score_it(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(WORDING)
        async with running(app_with(llm, make_app)) as client:
            owner = await sign_in(client, idp)
            resume_id, version_id = await generated(client, owner)

            other = bearer(idp.token(subject=str(uuid.uuid4()), email="eve@example.com"))
            await client.get("/api/v1/me", headers=other)
            report = await client.get(
                f"{RESUMES}/{resume_id}/versions/{version_id}/ats", headers=other
            )

        assert report.status_code == 404
