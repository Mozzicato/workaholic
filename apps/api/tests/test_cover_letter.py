"""Cover letters.

A letter is prose, which makes it the easiest place in the product to lie, and it is written
against a job advert, which is the most tempting thing to lie with. These tests pin both: the
letter may only claim what the candidate's own record says, and the advert may shape the letter
without ever supplying a claim to it.
"""

from typing import Any

import pytest

from tests.conftest import AppFactory, FakeIdentityProvider, running
from tests.test_resume_generation import PROFILE, ScriptedLLM, app_with, sign_in

RESUMES = "/api/v1/resumes"

ADVERT = (
    "Senior Platform Engineer. We need deep Kubernetes experience, Terraform, and someone who "
    "has run production systems serving millions of users across AWS."
)

FAITHFUL_LETTER: dict[str, Any] = {
    "paragraphs": [
        "I am writing about the Backend Engineer role at Lumen Freight.",
        "At Paystack I helped with the payouts reconciliation service, working in Python and "
        "PostgreSQL.",
        "I would be glad to talk it through.",
    ]
}

ADVERT_ECHOING_LETTER: dict[str, Any] = {
    "paragraphs": [
        "I am writing about the Senior Platform Engineer role.",
        "I have deep Kubernetes and Terraform experience running production systems on AWS for "
        "millions of users.",
        "I would be glad to talk it through.",
    ]
}


async def cover_letter(client: Any, headers: dict[str, str], title: str = "Lumen letter") -> str:
    await client.patch("/api/v1/profile", headers=headers, json=PROFILE)
    created = await client.post(
        RESUMES, headers=headers, json={"title": title, "document_type": "cover_letter"}
    )
    assert created.status_code == 201, created.text
    identifier: str = created.json()["id"]
    return identifier


@pytest.mark.usefixtures("db_engine")
class TestWritingALetter:
    async def test_a_letter_is_written_and_kept_as_a_version(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(FAITHFUL_LETTER)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            letter_id = await cover_letter(client, headers)

            response = await client.post(
                f"{RESUMES}/{letter_id}/versions",
                headers=headers,
                json={"brief": {"company": "Lumen Freight", "role": "Backend Engineer"}},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["schema_version"] == "1"
        assert body["prompt_version"] == "cover_letter.write.v1"
        content = body["content"]
        assert content["recipient"]["company"] == "Lumen Freight"
        assert content["salutation"] == "Dear hiring team,"
        assert len(content["paragraphs"]) == 3

    async def test_it_is_addressed_to_the_person_when_one_is_given(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(FAITHFUL_LETTER)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            letter_id = await cover_letter(client, headers)

            response = await client.post(
                f"{RESUMES}/{letter_id}/versions",
                headers=headers,
                json={
                    "brief": {"company": "Lumen Freight", "hiring_manager": "Ada Hiring"},
                },
            )

        content = response.json()["content"]
        assert content["salutation"] == "Dear Ada Hiring,"
        assert content["recipient"]["person"] == "Ada Hiring"

    async def test_the_sender_block_comes_from_the_record(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(FAITHFUL_LETTER)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            letter_id = await cover_letter(client, headers)

            response = await client.post(
                f"{RESUMES}/{letter_id}/versions",
                headers=headers,
                json={"brief": {"company": "Lumen Freight"}},
            )

        sender = response.json()["content"]["sender"]
        assert sender["full_name"] == "Ada Lovelace"
        assert sender["email"] == "ada@example.com"

    async def test_a_letter_needs_to_know_who_it_is_to(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM()
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            letter_id = await cover_letter(client, headers)

            response = await client.post(
                f"{RESUMES}/{letter_id}/versions", headers=headers, json={}
            )

        assert response.status_code == 422
        assert "company" in response.json()["error"]["message"]
        assert llm.calls == []


@pytest.mark.usefixtures("db_engine")
class TestTheAdvertCannotSupplyClaims:
    async def test_a_letter_that_answers_the_advert_with_invention_is_refused(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        """The whole point: the advert asks for Kubernetes, so a model offers Kubernetes."""
        llm = ScriptedLLM(ADVERT_ECHOING_LETTER, ADVERT_ECHOING_LETTER)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            letter_id = await cover_letter(client, headers)

            response = await client.post(
                f"{RESUMES}/{letter_id}/versions",
                headers=headers,
                json={
                    "brief": {
                        "company": "Lumen Freight",
                        "role": "Senior Platform Engineer",
                        "job_advert": ADVERT,
                    }
                },
            )
            versions = await client.get(f"{RESUMES}/{letter_id}/versions", headers=headers)

        assert response.status_code == 422
        error = response.json()["error"]
        assert error["code"] == "GENERATION_BLOCKED"
        invented = " ".join(detail["issue"] for detail in error["details"])
        assert "Kubernetes" in invented or "AWS" in invented or "Terraform" in invented
        assert versions.json() == [], "nothing is saved when a letter cannot be supported"

    async def test_the_advert_is_given_to_the_model_as_context(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(FAITHFUL_LETTER)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            letter_id = await cover_letter(client, headers)

            await client.post(
                f"{RESUMES}/{letter_id}/versions",
                headers=headers,
                json={"brief": {"company": "Lumen Freight", "job_advert": ADVERT}},
            )

        assert "Kubernetes" in llm.prompt_text, "the advert shapes the letter"
        assert "what the employer wants" in llm.prompt_text, "and is labelled as the employer's"

    async def test_a_second_attempt_names_what_was_invented(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(ADVERT_ECHOING_LETTER, FAITHFUL_LETTER)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            letter_id = await cover_letter(client, headers)

            response = await client.post(
                f"{RESUMES}/{letter_id}/versions",
                headers=headers,
                json={"brief": {"company": "Lumen Freight", "job_advert": ADVERT}},
            )

        assert response.status_code == 201
        assert len(llm.calls) == 2
        retry = llm.calls[1][-1].content
        assert "Kubernetes" in retry or "AWS" in retry


@pytest.mark.usefixtures("db_engine")
class TestRenderingALetter:
    async def test_it_previews_and_downloads_as_a_letter(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(FAITHFUL_LETTER)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            letter_id = await cover_letter(client, headers)
            created = await client.post(
                f"{RESUMES}/{letter_id}/versions",
                headers=headers,
                json={"brief": {"company": "Lumen Freight", "role": "Backend Engineer"}},
            )
            version_id = created.json()["id"]

            preview = await client.get(
                f"{RESUMES}/{letter_id}/versions/{version_id}/preview", headers=headers
            )

        assert preview.status_code == 200
        assert "Dear hiring team," in preview.text
        assert "Yours sincerely," in preview.text
        assert "Re: Backend Engineer" in preview.text
        assert "Ada Lovelace" in preview.text
        # A letter is prose: none of the resume furniture belongs on it.
        assert "Experience" not in preview.text
        assert "Skills" not in preview.text

    async def test_the_same_letter_renders_identically_every_time(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        """The date is written into the document, so rendering is not time-dependent."""
        llm = ScriptedLLM(FAITHFUL_LETTER)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            letter_id = await cover_letter(client, headers)
            created = await client.post(
                f"{RESUMES}/{letter_id}/versions",
                headers=headers,
                json={"brief": {"company": "Lumen Freight"}},
            )
            version_id = created.json()["id"]

            first = await client.get(
                f"{RESUMES}/{letter_id}/versions/{version_id}/preview", headers=headers
            )
            second = await client.get(
                f"{RESUMES}/{letter_id}/versions/{version_id}/preview", headers=headers
            )

        assert first.text == second.text

    async def test_a_resume_still_renders_as_a_resume(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        """The dispatch must not have changed what a resume does."""
        llm = ScriptedLLM(
            {
                "summary": "",
                "bullets": [
                    {"source_ids": ["e0.b0"], "text": "Helped build the payouts reconciliation"}
                ],
            }
        )
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            await client.patch("/api/v1/profile", headers=headers, json=PROFILE)
            created = await client.post(RESUMES, headers=headers, json={"title": "My resume"})
            resume_id = created.json()["id"]
            version = await client.post(f"{RESUMES}/{resume_id}/versions", headers=headers, json={})
            preview = await client.get(
                f"{RESUMES}/{resume_id}/versions/{version.json()['id']}/preview", headers=headers
            )

        assert preview.status_code == 200
        assert "Experience" in preview.text
        assert "Dear" not in preview.text
