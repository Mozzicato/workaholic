"""Every template: what each may change, and what none may.

A template is presentation. These tests hold every one of them to the same promises — every
fact reaches the page, nothing is fetched from outside, the typeface is carried in the page — and
check the few things that make each one what it is.
"""

import re
import uuid
from pathlib import Path

import pytest

from app.models.candidate import ResumeTemplate
from app.services.resume.rendering import render_html
from app.services.resume.templates import spec_for
from tests.conftest import AppFactory, FakeIdentityProvider, running
from tests.test_resume_generation import FAITHFUL, ScriptedLLM, app_with, set_up_record, sign_in
from tests.test_resume_rendering import DOCUMENT

ALL = list(ResumeTemplate)
FONT_DIR = Path(__file__).resolve().parents[1] / "app" / "templates" / "fonts"
STYLE_DIR = Path(__file__).resolve().parents[1] / "app" / "templates" / "resume" / "styles"

FACTS = (
    "Ada Lovelace",
    "ada@example.com",
    "+234 800 000 0000",
    "Lagos, Nigeria",
    "github.com/ada",
    "Backend engineer who works on payments systems.",
    "Paystack",
    "Backend Engineer",
    "Helped build the payouts reconciliation service",
    "Python",
    "PostgreSQL",
    "University of Lagos",
    "BSc",
    "Computer Science",
    "Bus tracker",
    "Tracked campus buses in real time",
    "TypeScript",
    "AZ-900",
    "Microsoft",
)


@pytest.mark.parametrize("template", ALL)
class TestEveryTemplate:
    def test_every_fact_reaches_the_page(self, template: ResumeTemplate) -> None:
        html = render_html(DOCUMENT, template)

        missing = [fact for fact in FACTS if fact not in html]
        assert missing == []

    def test_the_page_needs_nothing_from_outside(self, template: ResumeTemplate) -> None:
        """The PDF printer may not fetch anything. A font it has to download is a font it lacks."""
        style = render_html(DOCUMENT, template).split("<style>")[1].split("</style>")[0]

        urls = re.findall(r"url\(\"?([^\")]*)", style)
        assert urls, "a template carries its own fonts"
        assert all(url.startswith("data:font/woff2;base64,") for url in urls)
        assert "@import" not in style

    def test_it_carries_the_typeface_it_asks_for(self, template: ResumeTemplate) -> None:
        html = render_html(DOCUMENT, template)
        own = (STYLE_DIR / spec_for(template).stylesheet).read_text(encoding="utf-8")
        body = re.search(r"body \{[^}]*font-family: \"([^\"]+)\"", own)
        # A template that leaves the body font alone inherits the base serif.
        family = body.group(1) if body else "Source Serif 4"

        assert f'font-family: "{family}";' in html

    def test_it_is_deterministic(self, template: ResumeTemplate) -> None:
        assert render_html(DOCUMENT, template) == render_html(DOCUMENT, template)

    def test_user_text_cannot_inject_markup(self, template: ResumeTemplate) -> None:
        document = DOCUMENT.model_copy(update={"summary": "<script>alert(1)</script>"})

        html = render_html(document, template)

        assert "<script>" not in html


def test_every_font_file_ships_with_its_licence() -> None:
    stems = {path.name.rsplit("-", 2)[0] for path in FONT_DIR.glob("*.woff2")}

    assert stems
    for stem in stems:
        licence = FONT_DIR / f"LICENSE-{stem}.txt"
        assert licence.exists(), f"{stem} has no licence file"
        text = licence.read_text(encoding="utf-8")
        assert "Open Font License" in text or "Apache License" in text


def test_every_template_has_a_spec_and_a_stylesheet() -> None:
    for template in ALL:
        assert (STYLE_DIR / spec_for(template).stylesheet).exists()


class TestWhatMakesEachOneDifferent:
    def test_the_sidebar_puts_school_and_skills_beside_the_work(self) -> None:
        html = render_html(DOCUMENT, ResumeTemplate.SIDEBAR)
        aside = html.split('<aside class="side">')[1].split("</aside>")[0]
        main = html.split('<div class="main">')[1].split('<aside class="side">')[0]

        assert "University of Lagos" in aside
        assert "Python, TypeScript" in aside
        assert "Paystack" in main
        assert "Paystack" not in aside

    def test_classic_leads_with_education_and_puts_a_role_on_one_line(self) -> None:
        html = render_html(DOCUMENT, ResumeTemplate.CLASSIC)

        assert html.index("Education</h2>") < html.index("Experience</h2>")
        assert '<span class="entry-lead">Backend Engineer</span>' in html
        assert '<span class="entry-org">, Paystack</span>' in html

    def test_harvard_puts_the_organisation_before_the_role(self) -> None:
        html = render_html(DOCUMENT, ResumeTemplate.HARVARD)
        entry = html.split('<article class="entry entry-experience">')[1]

        assert entry.index("Paystack") < entry.index("Backend Engineer")

    def test_engineering_leads_with_skills(self) -> None:
        html = render_html(DOCUMENT, ResumeTemplate.ENGINEERING)

        assert html.index("Skills</h2>") < html.index("Experience</h2>")

    def test_new_templates_shorten_months_and_the_originals_do_not(self) -> None:
        assert "Mar 2024" in render_html(DOCUMENT, ResumeTemplate.CLASSIC)
        assert "March 2024" in render_html(DOCUMENT, ResumeTemplate.STANDARD)

    def test_a_link_prints_its_address_and_stays_clickable(self) -> None:
        html = render_html(DOCUMENT, ResumeTemplate.CLASSIC)

        assert '<a href="https://github.com/ada">github.com/ada</a>' in html
        assert '<a href="mailto:ada@example.com">ada@example.com</a>' in html

    def test_icons_are_decoration_not_text(self) -> None:
        """An ATS reads text; an icon must not stand in for a word it needs."""
        html = render_html(DOCUMENT, ResumeTemplate.MODERN)

        assert '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true">' in html
        assert "ada@example.com" in html


@pytest.mark.usefixtures("db_engine")
class TestChoosingATemplate:
    async def test_a_resume_starts_in_the_template_it_was_created_with(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(app_with(ScriptedLLM(), make_app)) as client:
            headers = await sign_in(client, idp)
            created = await client.post(
                "/api/v1/resumes", headers=headers, json={"title": "Mine", "template": "harvard"}
            )

        assert created.status_code == 201
        assert created.json()["template"] == "harvard"

    async def test_an_unknown_template_is_refused(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(app_with(ScriptedLLM(), make_app)) as client:
            headers = await sign_in(client, idp)
            created = await client.post(
                "/api/v1/resumes", headers=headers, json={"title": "Mine", "template": "fancy"}
            )

        assert created.status_code == 422

    async def test_a_draft_is_written_in_the_resume_s_template(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(app_with(ScriptedLLM(FAITHFUL), make_app)) as client:
            headers = await sign_in(client, idp)
            resume_id = await set_up_record(client, headers)
            await client.patch(
                f"/api/v1/resumes/{resume_id}", headers=headers, json={"template": "modern"}
            )

            version = await client.post(
                f"/api/v1/resumes/{resume_id}/versions", headers=headers, json={}
            )

        assert version.status_code == 201
        assert version.json()["template"] == "modern"

    async def test_changing_the_template_needs_no_new_draft(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        """A template is only the look: any version can be shown in any template, as it is."""
        llm = ScriptedLLM(FAITHFUL)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            resume_id = await set_up_record(client, headers)
            version_id = (
                await client.post(f"/api/v1/resumes/{resume_id}/versions", headers=headers, json={})
            ).json()["id"]
            calls_after_writing = len(llm.calls)

            preview = f"/api/v1/resumes/{resume_id}/versions/{version_id}/preview"
            own = await client.get(preview, headers=headers)
            harvard = await client.get(f"{preview}?template=harvard", headers=headers)

        assert own.status_code == harvard.status_code == 200
        assert "template-classic" in own.text
        assert "template-harvard" in harvard.text
        assert "Helped build the payouts reconciliation service" in harvard.text
        assert len(llm.calls) == calls_after_writing  # nothing was rewritten

    async def test_a_template_cannot_be_cleared(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(app_with(ScriptedLLM(), make_app)) as client:
            headers = await sign_in(client, idp)
            resume_id = (
                await client.post("/api/v1/resumes", headers=headers, json={"title": "Mine"})
            ).json()["id"]

            updated = await client.patch(
                f"/api/v1/resumes/{resume_id}", headers=headers, json={"template": None}
            )

        assert updated.status_code == 200
        assert updated.json()["template"] == "classic"

    async def test_another_account_cannot_preview_a_version_in_any_template(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(app_with(ScriptedLLM(FAITHFUL), make_app)) as client:
            owner = await sign_in(client, idp)
            resume_id = await set_up_record(client, owner)
            version_id = (
                await client.post(f"/api/v1/resumes/{resume_id}/versions", headers=owner, json={})
            ).json()["id"]
            intruder = await sign_in(client, idp)

            response = await client.get(
                f"/api/v1/resumes/{resume_id}/versions/{version_id}/preview?template=bold",
                headers=intruder,
            )

        assert response.status_code == 404
        assert uuid.UUID(version_id)
