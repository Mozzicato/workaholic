"""The PDF step, against a real browser.

These tests print actual PDFs. They are skipped when Chromium is not installed, so a checkout
without `playwright install chromium` still runs the rest of the suite; CI installs it.
"""

import io
import uuid
from typing import Any

import pytest
from playwright.async_api import Error as PlaywrightError
from pypdf import PdfReader

from app.models.candidate import ResumeTemplate
from app.services.resume.pdf import PdfRenderer
from app.services.resume.rendering import render_html
from tests.conftest import AppFactory, FakeIdentityProvider, bearer, running
from tests.test_resume_generation import (
    FAITHFUL,
    PROFILE,
    ScriptedLLM,
    app_with,
    set_up_record,
    sign_in,
)
from tests.test_resume_rendering import DOCUMENT

pytestmark = pytest.mark.pdf

PDF_HEADER = b"%PDF-"


@pytest.fixture(scope="module")
async def renderer() -> Any:
    instance = PdfRenderer()
    try:
        await instance.start()
    except PlaywrightError as exc:  # pragma: no cover - depends on the machine
        pytest.skip(f"Chromium is not installed: {exc}")
    try:
        yield instance
    finally:
        await instance.stop()


class TestRendering:
    async def test_a_document_prints_to_a_pdf(self, renderer: PdfRenderer) -> None:
        content = await renderer.render(render_html(DOCUMENT, ResumeTemplate.STANDARD))

        assert content.startswith(PDF_HEADER)
        assert len(content) > 1000

    @pytest.mark.parametrize("template", list(ResumeTemplate))
    async def test_every_template_prints_text_an_ats_can_read_back(
        self, renderer: PdfRenderer, template: ResumeTemplate
    ) -> None:
        """What an ATS does: open the PDF and read the text out. Every template must survive it."""
        content = await renderer.render(render_html(DOCUMENT, template))
        text = " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
        flat = " ".join(text.split())

        assert content.startswith(PDF_HEADER)
        for fact in (
            "Ada Lovelace",
            "ada@example.com",
            "Paystack",
            "Helped build the payouts reconciliation service",
            "University of Lagos",
            "Bus tracker",
            "AZ-900",
        ):
            assert fact in flat, f"{template.value}: {fact!r} did not read back"

    async def test_the_text_is_selectable_rather_than_an_image(self, renderer: PdfRenderer) -> None:
        """An ATS reads text. A resume rendered as pixels is worthless to the person holding it."""
        content = await renderer.render(render_html(DOCUMENT, ResumeTemplate.STANDARD))

        assert b"/Font" in content
        assert b"/BaseFont" in content  # a real embedded face, not a picture of one
        # "/ImageB", "/ImageC" and "/ImageI" are procedure-set boilerplate in every PDF;
        # an actual picture would be an XObject with this subtype.
        assert b"/Subtype /Image" not in content
        assert b"/Subtype/Image" not in content

    async def test_one_page_of_content_stays_one_page(self, renderer: PdfRenderer) -> None:
        content = await renderer.render(render_html(DOCUMENT, ResumeTemplate.STANDARD))

        assert content.count(b"/Type /Page\n") <= 1 or b"/Count 1" in content

    async def test_a_second_render_is_unaffected_by_the_first(self, renderer: PdfRenderer) -> None:
        first = await renderer.render(render_html(DOCUMENT, ResumeTemplate.STANDARD))
        second = await renderer.render(render_html(DOCUMENT, ResumeTemplate.STANDARD))

        assert first.startswith(PDF_HEADER)
        assert second.startswith(PDF_HEADER)
        assert abs(len(first) - len(second)) < 200  # only the embedded timestamp differs

    async def test_text_survives_the_round_trip_into_a_pdf_and_back_out(
        self, renderer: PdfRenderer
    ) -> None:
        """What an applicant tracking system does: read the text back out of the file."""
        from app.services.documents import extract_text, pdf_text

        content = await renderer.render(render_html(DOCUMENT, ResumeTemplate.STANDARD))

        read_back = pdf_text(content)
        assert "Ada Lovelace" in read_back
        assert "payouts reconciliation" in read_back

        # And the same file read as an upload, which is the other direction users use.
        extracted = extract_text(content)
        assert extracted.kind.value == "pdf"
        assert extracted.pages == 1
        assert "Lumen" in extracted.text or "Paystack" in extracted.text

    async def test_a_dead_browser_is_replaced_rather_than_failing_every_later_request(
        self, renderer: PdfRenderer
    ) -> None:
        await renderer.stop()

        content = await renderer.render(render_html(DOCUMENT, ResumeTemplate.STANDARD))

        assert content.startswith(PDF_HEADER)


@pytest.mark.usefixtures("db_engine")
class TestDownloadEndpoint:
    async def test_a_generated_version_can_be_downloaded(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(FAITHFUL)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            resume_id = await set_up_record(client, headers, profile=PROFILE)
            created = await client.post(
                f"/api/v1/resumes/{resume_id}/versions", headers=headers, json={}
            )
            version_id = created.json()["id"]

            preview = await client.get(
                f"/api/v1/resumes/{resume_id}/versions/{version_id}/preview", headers=headers
            )
            pdf = await client.get(
                f"/api/v1/resumes/{resume_id}/versions/{version_id}/pdf", headers=headers
            )

        assert preview.status_code == 200
        assert preview.headers["content-type"].startswith("text/html")
        assert preview.headers["cache-control"] == "no-store"
        assert "Helped build the payouts reconciliation service" in preview.text

        assert pdf.status_code == 200
        assert pdf.headers["content-type"] == "application/pdf"
        assert pdf.headers["cache-control"] == "no-store"
        assert pdf.headers["content-disposition"] == 'attachment; filename="Backend-resume-v1.pdf"'
        assert pdf.content.startswith(PDF_HEADER)

    async def test_another_account_cannot_download_it(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(FAITHFUL)
        async with running(app_with(llm, make_app)) as client:
            owner = await sign_in(client, idp)
            resume_id = await set_up_record(client, owner, profile=PROFILE)
            created = await client.post(
                f"/api/v1/resumes/{resume_id}/versions", headers=owner, json={}
            )
            version_id = created.json()["id"]

            intruder = bearer(idp.token(subject=str(uuid.uuid4()), email="eve@example.com"))
            await client.get("/api/v1/me", headers=intruder)
            preview = await client.get(
                f"/api/v1/resumes/{resume_id}/versions/{version_id}/preview", headers=intruder
            )
            pdf = await client.get(
                f"/api/v1/resumes/{resume_id}/versions/{version_id}/pdf", headers=intruder
            )

        assert preview.status_code == 404
        assert pdf.status_code == 404

    async def test_downloading_requires_signing_in(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        llm = ScriptedLLM(FAITHFUL)
        async with running(app_with(llm, make_app)) as client:
            headers = await sign_in(client, idp)
            resume_id = await set_up_record(client, headers, profile=PROFILE)
            created = await client.post(
                f"/api/v1/resumes/{resume_id}/versions", headers=headers, json={}
            )
            version_id = created.json()["id"]

            response = await client.get(f"/api/v1/resumes/{resume_id}/versions/{version_id}/pdf")

        assert response.status_code == 401
