"""A resume is not written until the record holds what a resume needs."""

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.services.resume.readiness import DocumentKind, assess_readiness
from tests.conftest import AppFactory, FakeIdentityProvider, bearer, running
from tests.test_resume_generation import PROFILE, ScriptedLLM, app_with, set_up_record, sign_in


def record(**sections: Any) -> SimpleNamespace:
    empty: dict[str, Any] = {
        "basics": {},
        "experience": [],
        "education": [],
        "projects": [],
        "skills": [],
    }
    return SimpleNamespace(**{**empty, **sections})


COMPLETE = record(
    basics={"full_name": "Ada Lovelace", "phone": "+234 801 234 5678"},
    education=[{"institution": "University of Lagos"}],
    experience=[{"employer": "Paystack", "title": "Intern", "bullets": ["Wrote payout tests"]}],
    skills=[{"name": "Python"}],
)


def missing(profile: SimpleNamespace, kind: DocumentKind = DocumentKind.RESUME) -> list[str]:
    return [item.key for item in assess_readiness(profile, kind).missing]


def test_a_complete_record_is_ready() -> None:
    assert assess_readiness(COMPLETE).ready


def test_an_empty_record_needs_everything() -> None:
    assert missing(record()) == ["name", "contact", "education", "experience_or_projects", "skills"]


def test_a_project_is_enough_without_a_job() -> None:
    """Someone who has not had a job must not be pushed to invent one."""
    student = record(
        basics=COMPLETE.basics,
        education=COMPLETE.education,
        projects=[{"name": "Campus map", "description": "An offline map of the campus"}],
        skills=COMPLETE.skills,
    )
    assert assess_readiness(student).ready


def test_a_role_with_no_line_about_it_does_not_count() -> None:
    bare = record(
        basics=COMPLETE.basics,
        education=COMPLETE.education,
        experience=[{"employer": "Paystack", "title": "Intern", "bullets": []}],
        skills=COMPLETE.skills,
    )
    assert missing(bare) == ["experience_or_projects"]


def test_email_or_phone_is_contact_enough() -> None:
    by_email = record(**{**vars(COMPLETE), "basics": {"full_name": "Ada", "email": "a@b.dev"}})
    assert assess_readiness(by_email).ready


def test_a_cover_letter_does_not_need_education_or_skills() -> None:
    letter = record(basics=COMPLETE.basics, experience=COMPLETE.experience)
    assert assess_readiness(letter, DocumentKind.COVER_LETTER).ready
    assert missing(letter) == ["education", "skills"]


@pytest.mark.usefixtures("db_engine")
class TestGate:
    async def test_no_resume_is_written_without_education(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM()
        no_school = {**PROFILE, "education": []}
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            resume_id = await set_up_record(client, headers, profile=no_school)

            response = await client.post(
                f"/api/v1/resumes/{resume_id}/versions", headers=headers, json={}
            )

        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "PROFILE_INCOMPLETE"
        assert [detail["field"] for detail in error["details"]] == ["education"]
        assert llm.calls == []  # refused before any model was asked

    async def test_readiness_reports_each_item(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(make_app()) as client:
            headers = bearer(idp.token(subject=str(uuid.uuid4()), email="ada@example.com"))
            await client.get("/api/v1/me", headers=headers)
            before = (await client.get("/api/v1/profile/readiness", headers=headers)).json()
            await client.patch("/api/v1/profile", headers=headers, json=PROFILE)
            after = (await client.get("/api/v1/profile/readiness", headers=headers)).json()

        assert before["resume_ready"] is False
        assert [item["done"] for item in before["items"]] == [False] * 5
        assert after["resume_ready"] is True
        assert after["cover_letter_ready"] is True

    async def test_readiness_needs_a_signed_in_user(self, make_app: AppFactory) -> None:
        async with running(make_app()) as client:
            response = await client.get("/api/v1/profile/readiness")
        assert response.status_code == 401
