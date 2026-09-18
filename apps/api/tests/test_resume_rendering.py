"""The renderer: it must add nothing, lose nothing, and do the same thing every time."""

import pytest

from app.models.candidate import ResumeTemplate
from app.schemas.resume_document import (
    Bullet,
    ResumeBasics,
    ResumeCertification,
    ResumeDocument,
    ResumeEducation,
    ResumeExperience,
    ResumeLink,
    ResumeProject,
    ResumeSkillGroup,
)
from app.services.resume.rendering import (
    _EN_DASH,
    format_month,
    format_range,
    render_html,
)

DOCUMENT = ResumeDocument(
    basics=ResumeBasics(
        full_name="Ada Lovelace",
        headline="Backend engineer",
        email="ada@example.com",
        phone="+234 800 000 0000",
        location="Lagos, Nigeria",
        links=[ResumeLink(label="Github", url="https://github.com/ada")],
    ),
    summary="Backend engineer who works on payments systems.",
    experience=[
        ResumeExperience(
            item_id="role-1",
            employer="Paystack",
            title="Backend Engineer",
            location="Lagos, Nigeria",
            is_current=True,
            start_date="2024-03",
            bullets=[
                Bullet(
                    text="Helped build the payouts reconciliation service",
                    source_item_id="role-1",
                    source_bullet_index=0,
                )
            ],
            technologies=["Python", "PostgreSQL"],
        )
    ],
    education=[
        ResumeEducation(
            item_id="edu-1",
            institution="University of Lagos",
            qualification="BSc",
            field_of_study="Computer Science",
            start_date="2022",
            end_date="2026",
        )
    ],
    projects=[
        ResumeProject(
            item_id="project-1",
            name="Bus tracker",
            url="https://example.com/bus",
            bullets=[
                Bullet(
                    text="Tracked campus buses in real time",
                    source_item_id="project-1",
                    source_bullet_index=0,
                )
            ],
        )
    ],
    skills=[ResumeSkillGroup(category="Languages", skills=["Python", "TypeScript"])],
    certifications=[
        ResumeCertification(
            item_id="cert-1", name="AZ-900", issuer="Microsoft", issued_date="2025-04"
        )
    ],
)


class TestContent:
    def test_every_fact_in_the_document_reaches_the_page(self) -> None:
        html = render_html(DOCUMENT, ResumeTemplate.STANDARD)

        for expected in (
            "Ada Lovelace",
            "Backend engineer",
            "ada@example.com",
            "+234 800 000 0000",
            "Lagos, Nigeria",
            "https://github.com/ada",
            "Backend engineer who works on payments systems.",
            "Paystack",
            "Helped build the payouts reconciliation service",
            "Python, PostgreSQL",
            "University of Lagos",
            "Bus tracker",
            "Tracked campus buses in real time",
            "Python, TypeScript",
            "AZ-900",
            "Microsoft",
        ):
            assert expected in html

    def test_a_current_role_reads_as_present(self) -> None:
        assert f"March 2024 {_EN_DASH} Present" in render_html(DOCUMENT, ResumeTemplate.STANDARD)

    def test_user_text_cannot_inject_markup(self) -> None:
        document = DOCUMENT.model_copy(update={"summary": "<script>alert(1)</script> & co"})

        html = render_html(document, ResumeTemplate.STANDARD)

        assert "<script>" not in html
        assert "&lt;script&gt;" in html
        assert "&amp; co" in html

    def test_an_empty_section_is_left_out_rather_than_left_blank(self) -> None:
        document = DOCUMENT.model_copy(update={"certifications": [], "summary": None})

        html = render_html(document, ResumeTemplate.STANDARD)

        assert "Certifications" not in html
        assert "Summary" not in html


class TestTemplates:
    @pytest.mark.parametrize("template", list(ResumeTemplate))
    def test_each_template_renders_a_complete_page(self, template: ResumeTemplate) -> None:
        html = render_html(DOCUMENT, template)

        assert html.startswith("<!doctype html>")
        assert "Ada Lovelace" in html
        assert "Helped build the payouts reconciliation service" in html
        assert html.rstrip().endswith("</html>")

    def test_the_academic_template_leads_with_education(self) -> None:
        html = render_html(DOCUMENT, ResumeTemplate.ACADEMIC)

        assert html.index("Education") < html.index("Experience")

    def test_the_standard_template_leads_with_experience(self) -> None:
        html = render_html(DOCUMENT, ResumeTemplate.STANDARD)

        assert html.index("Experience") < html.index("Education")

    def test_templates_differ_only_in_presentation(self) -> None:
        standard = render_html(DOCUMENT, ResumeTemplate.STANDARD)
        compact = render_html(DOCUMENT, ResumeTemplate.COMPACT)

        assert standard != compact
        for fact in ("Ada Lovelace", "Paystack", "University of Lagos", "AZ-900"):
            assert fact in standard
            assert fact in compact

    def test_the_stylesheet_survives_escaping_intact(self) -> None:
        """Escaping the CSS silently breaks every rule containing a quote — fonts, separators."""
        html = render_html(DOCUMENT, ResumeTemplate.STANDARD)
        style = html.split("<style>")[1].split("</style>")[0]

        assert "&quot;" not in style
        assert "&#34;" not in style
        assert 'content: " · "' in style  # the separator between contact details
        assert '"Georgia"' in style  # a quoted font family reached the page unmangled

    def test_the_stylesheet_is_inlined_so_the_page_stands_alone(self) -> None:
        html = render_html(DOCUMENT, ResumeTemplate.STANDARD)

        assert "<style>" in html
        assert "@page" in html
        assert "<link" not in html
        assert "http://" not in html.split("<style>")[1].split("</style>")[0]


class TestDeterminism:
    def test_the_same_document_renders_identically(self) -> None:
        assert render_html(DOCUMENT, ResumeTemplate.STANDARD) == render_html(
            DOCUMENT, ResumeTemplate.STANDARD
        )

    def test_nothing_generated_at_render_time_leaks_in(self) -> None:
        html = render_html(DOCUMENT, ResumeTemplate.STANDARD)

        # No "generated on" date, and no internal identifiers on the page.
        assert "role-1" not in html
        assert "project-1" not in html
        assert "schema_version" not in html


class TestDates:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [("2025-06", "June 2025"), ("2025-01", "January 2025"), ("2025", "2025"), (None, "")],
    )
    def test_months_read_as_words(self, value: str | None, expected: str) -> None:
        assert format_month(value) == expected

    def test_a_range_needs_only_one_end(self) -> None:
        assert format_range("2024-03", None, False) == "March 2024"
        assert format_range(None, "2025-06", False) == "June 2025"
        assert format_range(None, None, False) == ""

    def test_a_current_role_has_no_end_date(self) -> None:
        assert format_range("2024-03", None, True) == f"March 2024 {_EN_DASH} Present"
