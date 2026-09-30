"""What we say about a skill the job wants and the person does not have.

The temptation this feature creates is obvious: add the keyword and move on. So the tests here
are mostly about what it refuses to do — nothing it produces ever reaches a resume.
"""

import uuid
from typing import Any

import httpx
import pytest

from app.services.job.coaching import coach
from tests.conftest import AppFactory, FakeIdentityProvider, bearer, running
from tests.test_resume_generation import ScriptedLLM, app_with

ADVERT = """Junior Backend Engineer at Northwind Payments.

You will work on our merchant dashboard. We use Python and PostgreSQL.

Requirements: Python, SQL, Git.
Nice to have: Kubernetes, Kafka, AWS, Go.
"""

ANALYSIS: dict[str, Any] = {
    "role": "Junior Backend Engineer",
    "seniority": "junior",
    "required_skills": ["Python", "SQL", "Git"],
    "preferred_skills": ["Kubernetes", "Kafka", "AWS", "Go"],
    "responsibilities": ["Work on the merchant dashboard"],
    "qualifications": [],
    "keywords": ["Python", "PostgreSQL"],
    "domain_terms": ["payments"],
    "education_requirements": [],
    "experience_requirements": [],
}

RECORD: dict[str, Any] = {
    "basics": {"full_name": "Ifeoma Chukwu", "email": "ifeoma@example.com"},
    "education": [{"institution": "University of Lagos", "qualification": "BSc"}],
    "experience": [
        {
            "employer": "Andela",
            "title": "Intern",
            "bullets": ["deployed the service with docker compose, 40 staff used it daily"],
            "technologies": ["Python", "Docker"],
        }
    ],
    "projects": [],
    "skills": [{"name": "Python"}, {"name": "SQL"}, {"name": "Git"}, {"name": "Docker"}],
}


class TestWhatToSayAndWhatToBuild:
    def test_something_adjacent_they_really_did_is_surfaced(self) -> None:
        """ "You have never used Kubernetes, but you have used Docker" is worth saying out loud."""
        coaching = coach(["Kubernetes"], record_terms=["Docker", "Python"])

        assert coaching.gaps[0].skill == "Kubernetes"
        assert "docker" in coaching.gaps[0].adjacent

    def test_nothing_adjacent_is_claimed_when_there_is_nothing(self) -> None:
        coaching = coach(["Kubernetes"], record_terms=["Excel", "Word"])

        assert coaching.gaps[0].adjacent == ()

    def test_each_gap_gets_something_finishable_to_build(self) -> None:
        coaching = coach(["Kafka", "AWS"], record_terms=["Python"])

        titles = [idea.title for idea in coaching.ideas]
        assert len(titles) == len(set(titles))
        assert all(idea.steps for idea in coaching.ideas)

    def test_an_unknown_skill_still_gets_honest_advice(self) -> None:
        coaching = coach(["Fortran 77"], record_terms=["Python"])

        assert coaching.ideas
        assert "README" in coaching.ideas[0].steps[-1]

    def test_it_never_suggests_more_than_a_person_can_do(self) -> None:
        coaching = coach(["Kubernetes", "Kafka", "AWS", "React", "SQL", "Testing"], record_terms=[])

        assert len(coaching.ideas) <= 3

    def test_nothing_to_advise_when_nothing_is_missing(self) -> None:
        coaching = coach([], record_terms=["Python"])

        assert coaching.gaps == []
        assert coaching.ideas == []

    def test_the_caveat_says_it_is_not_on_the_resume(self) -> None:
        coaching = coach(["Kubernetes"], record_terms=[])

        assert "will not be added" in coaching.caveat


@pytest.mark.usefixtures("db_engine")
class TestTheEndpoint:
    async def test_it_coaches_on_what_the_job_wants_and_the_record_lacks(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(ANALYSIS)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            await client.patch("/api/v1/profile", headers=headers, json=RECORD)
            job = await client.post(
                "/api/v1/jobs",
                headers=headers,
                json={"title": "Junior Backend Engineer", "raw_text": ADVERT},
            )
            job_id = job.json()["id"]

            response = await client.get(f"/api/v1/jobs/{job_id}/coaching", headers=headers)

        assert response.status_code == 200
        body = response.json()
        missing = {gap["skill"] for gap in body["gaps"]}
        assert {"Kubernetes", "Kafka"} <= missing
        assert "Python" not in missing  # she has it; it is not a gap
        kubernetes = next(gap for gap in body["gaps"] if gap["skill"] == "Kubernetes")
        assert "docker" in kubernetes["adjacent"]
        assert body["ideas"]
        assert "will not be added" in body["caveat"]

    async def test_coaching_adds_nothing_to_the_record(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        """The whole point: a skill they lack stays missing until they have used it."""
        llm = ScriptedLLM(ANALYSIS)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            await client.patch("/api/v1/profile", headers=headers, json=RECORD)
            job = await client.post(
                "/api/v1/jobs",
                headers=headers,
                json={"title": "Junior Backend Engineer", "raw_text": ADVERT},
            )

            await client.get(f"/api/v1/jobs/{job.json()['id']}/coaching", headers=headers)
            profile = await client.get("/api/v1/profile", headers=headers)

        skills = {item["name"] for item in profile.json()["skills"]}
        assert "Kubernetes" not in skills
        assert "Kafka" not in skills
        assert skills == {"Python", "SQL", "Git", "Docker"}

    async def test_another_account_cannot_see_it(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(ANALYSIS)
        async with running(app_with(llm, make_app)) as client:
            owner = await sign_in(client, idp)
            job = await client.post(
                "/api/v1/jobs", headers=owner, json={"title": "Role", "raw_text": ADVERT}
            )
            intruder = await sign_in(client, idp)

            response = await client.get(
                f"/api/v1/jobs/{job.json()['id']}/coaching", headers=intruder
            )

        assert response.status_code == 404


async def sign_in(client: httpx.AsyncClient, idp: FakeIdentityProvider) -> dict[str, str]:
    headers = bearer(idp.token(subject=str(uuid.uuid4()), email="ifeoma@example.com"))
    await client.get("/api/v1/me", headers=headers)
    return headers
