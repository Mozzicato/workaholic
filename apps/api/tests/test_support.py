"""Feedback, sent-in templates, and the administrator's dashboard.

The dashboard is the one place in Workaholic where someone can see across accounts, so most of
what is tested here is what it must *not* show.
"""

import uuid
from typing import Any

import httpx
import pytest

from app.core.config import get_settings
from tests.conftest import AppFactory, FakeIdentityProvider, bearer, running

ADMIN_EMAIL = "boss@workaholic.dev"
PDF = b"%PDF-1.4\n%fake but shaped like a pdf\n"


@pytest.fixture(autouse=True)
def _admins(monkeypatch: pytest.MonkeyPatch) -> Any:
    """One named administrator, as production has."""
    settings = get_settings()
    monkeypatch.setattr(settings, "admin_emails", [ADMIN_EMAIL], raising=False)
    return settings


async def sign_in(
    client: httpx.AsyncClient, idp: FakeIdentityProvider, email: str
) -> dict[str, str]:
    headers = bearer(idp.token(subject=str(uuid.uuid4()), email=email))
    await client.get("/api/v1/me", headers=headers)
    return headers


@pytest.mark.usefixtures("db_engine")
class TestFeedback:
    async def test_a_message_reaches_the_administrator(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(make_app()) as client:
            user = await sign_in(client, idp, "ada@example.com")
            sent = await client.post(
                "/api/v1/feedback",
                headers=user,
                json={"message": "The mic button is hard to find", "page": "/assistant"},
            )

            admin = await sign_in(client, idp, ADMIN_EMAIL)
            listed = await client.get("/api/v1/admin/feedback", headers=admin)

        assert sent.status_code == 201
        assert sent.json()["email"] == "ada@example.com"
        assert [entry["message"] for entry in listed.json()] == ["The mic button is hard to find"]
        assert listed.json()[0]["page"] == "/assistant"
        assert listed.json()[0]["status"] == "new"

    async def test_an_empty_message_is_refused(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(make_app()) as client:
            user = await sign_in(client, idp, "ada@example.com")
            response = await client.post("/api/v1/feedback", headers=user, json={"message": "  "})

        assert response.status_code == 422

    async def test_feedback_needs_signing_in(self, make_app: AppFactory) -> None:
        async with running(make_app()) as client:
            response = await client.post("/api/v1/feedback", json={"message": "hi"})

        assert response.status_code == 401

    async def test_one_user_cannot_read_another_s_feedback(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(make_app()) as client:
            ada = await sign_in(client, idp, "ada@example.com")
            await client.post("/api/v1/feedback", headers=ada, json={"message": "private"})
            eve = await sign_in(client, idp, "eve@example.com")

            response = await client.get("/api/v1/admin/feedback", headers=eve)

        assert response.status_code == 403
        assert "private" not in response.text


@pytest.mark.usefixtures("db_engine")
class TestSendingATemplate:
    async def test_a_template_is_kept_for_the_team_to_look_at(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(make_app()) as client:
            user = await sign_in(client, idp, "ada@example.com")
            sent = await client.post(
                "/api/v1/template-requests",
                headers=user,
                files={"file": ("my-template.pdf", PDF, "application/pdf")},
                data={"note": "my school uses this"},
            )

            admin = await sign_in(client, idp, ADMIN_EMAIL)
            listed = await client.get("/api/v1/admin/template-requests", headers=admin)
            request_id = listed.json()[0]["id"]
            downloaded = await client.get(
                f"/api/v1/admin/template-requests/{request_id}/file", headers=admin
            )

        assert sent.status_code == 201
        assert sent.json()["filename"] == "my-template.pdf"
        assert listed.json()[0]["note"] == "my school uses this"
        assert downloaded.content == PDF

    async def test_a_file_that_is_not_a_document_is_refused(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(make_app()) as client:
            user = await sign_in(client, idp, "ada@example.com")
            response = await client.post(
                "/api/v1/template-requests",
                headers=user,
                files={"file": ("nice.png", b"\x89PNG\r\n\x1a\n" + b"0" * 100, "image/png")},
            )

        assert response.status_code == 422

    async def test_it_never_enters_anyone_s_record(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        """A sent-in template is a message to the team, not a document to read into a profile."""
        async with running(make_app()) as client:
            user = await sign_in(client, idp, "ada@example.com")
            await client.post(
                "/api/v1/template-requests",
                headers=user,
                files={"file": ("template.pdf", PDF, "application/pdf")},
            )

            profile = await client.get("/api/v1/profile", headers=user)
            evidence = await client.get("/api/v1/evidence", headers=user)

        assert profile.json()["experience"] == []
        assert evidence.json() == []

    async def test_a_sent_template_can_be_deleted_once_it_is_built(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(make_app()) as client:
            user = await sign_in(client, idp, "ada@example.com")
            await client.post(
                "/api/v1/template-requests",
                headers=user,
                files={"file": ("template.pdf", PDF, "application/pdf")},
            )
            admin = await sign_in(client, idp, ADMIN_EMAIL)
            request_id = (
                await client.get("/api/v1/admin/template-requests", headers=admin)
            ).json()[0]["id"]

            deleted = await client.delete(
                f"/api/v1/admin/template-requests/{request_id}", headers=admin
            )
            remaining = await client.get("/api/v1/admin/template-requests", headers=admin)

        assert deleted.status_code == 204
        assert remaining.json() == []


@pytest.mark.usefixtures("db_engine")
class TestTheDashboard:
    async def test_only_a_named_administrator_may_open_it(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(make_app()) as client:
            ordinary = await sign_in(client, idp, "ada@example.com")
            admin = await sign_in(client, idp, ADMIN_EMAIL)

            refused = await client.get("/api/v1/admin/stats", headers=ordinary)
            allowed = await client.get("/api/v1/admin/stats", headers=admin)
            anonymous = await client.get("/api/v1/admin/stats")

        assert refused.status_code == 403
        assert refused.json()["error"]["code"] == "FORBIDDEN"
        assert allowed.status_code == 200
        assert anonymous.status_code == 401

    async def test_the_account_page_says_who_is_an_administrator(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(make_app()) as client:
            ordinary = await sign_in(client, idp, "ada@example.com")
            admin = await sign_in(client, idp, ADMIN_EMAIL)

            theirs = await client.get("/api/v1/me", headers=ordinary)
            mine = await client.get("/api/v1/me", headers=admin)

        assert theirs.json()["is_admin"] is False
        assert mine.json()["is_admin"] is True

    async def test_it_counts_what_happened_without_reading_any_of_it(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(make_app()) as client:
            ada = await sign_in(client, idp, "ada@example.com")
            await client.patch(
                "/api/v1/profile",
                headers=ada,
                json={
                    "basics": {"full_name": "Ada Lovelace", "email": "ada@example.com"},
                    "education": [{"institution": "University of Lagos"}],
                    "experience": [
                        {
                            "employer": "Paystack",
                            "title": "Engineer",
                            "bullets": ["a secret only she should see"],
                        }
                    ],
                    "skills": [{"name": "Python"}],
                },
            )
            await client.post(
                "/api/v1/resumes", headers=ada, json={"title": "Mine", "template": "modern"}
            )

            admin = await sign_in(client, idp, ADMIN_EMAIL)
            stats = await client.get("/api/v1/admin/stats", headers=admin)

        body = stats.json()
        assert body["users_total"] >= 2
        assert body["resumes_total"] == 1
        assert body["records_ready_for_a_resume"] == 1
        assert body["templates_in_use"] == [{"label": "modern", "count": 1}]
        # Nothing anybody wrote is in this response.
        assert "a secret only she should see" not in stats.text
        assert "Paystack" not in stats.text
        assert "University of Lagos" not in stats.text

    async def test_an_account_can_be_erased_but_not_the_administrator_s_own(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(make_app()) as client:
            ada = await sign_in(client, idp, "ada@example.com")
            await client.post("/api/v1/resumes", headers=ada, json={"title": "Mine"})
            admin = await sign_in(client, idp, ADMIN_EMAIL)
            accounts = (await client.get("/api/v1/admin/users", headers=admin)).json()
            theirs = next(row for row in accounts if row["email"] == "ada@example.com")
            mine = next(row for row in accounts if row["email"] == ADMIN_EMAIL)

            refused = await client.delete(f"/api/v1/admin/users/{mine['id']}", headers=admin)
            deleted = await client.delete(f"/api/v1/admin/users/{theirs['id']}", headers=admin)
            left = (await client.get("/api/v1/admin/users", headers=admin)).json()

        assert refused.status_code == 422
        assert deleted.status_code == 204
        assert [row["email"] for row in left] == [ADMIN_EMAIL]

    async def test_erasing_an_account_keeps_the_feedback_it_left(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        """A complaint is worth acting on after the person who made it has gone."""
        async with running(make_app()) as client:
            ada = await sign_in(client, idp, "ada@example.com")
            await client.post("/api/v1/feedback", headers=ada, json={"message": "too slow"})
            admin = await sign_in(client, idp, ADMIN_EMAIL)
            accounts = (await client.get("/api/v1/admin/users", headers=admin)).json()
            theirs = next(row for row in accounts if row["email"] == "ada@example.com")

            await client.delete(f"/api/v1/admin/users/{theirs['id']}", headers=admin)
            feedback = await client.get("/api/v1/admin/feedback", headers=admin)

        assert [entry["message"] for entry in feedback.json()] == ["too slow"]

    async def test_a_message_can_be_marked_done(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(make_app()) as client:
            ada = await sign_in(client, idp, "ada@example.com")
            await client.post("/api/v1/feedback", headers=ada, json={"message": "a bug"})
            admin = await sign_in(client, idp, ADMIN_EMAIL)
            entry_id = (await client.get("/api/v1/admin/feedback", headers=admin)).json()[0]["id"]

            updated = await client.patch(
                f"/api/v1/admin/feedback/{entry_id}", headers=admin, json={"status": "done"}
            )

        assert updated.status_code == 200
        assert updated.json()["status"] == "done"
        assert updated.json()["handled_at"] is not None
