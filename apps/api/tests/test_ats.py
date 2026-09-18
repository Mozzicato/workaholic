"""The Workaholic ATS Compatibility Score (PRD §34, §35).

The number goes in front of someone deciding whether to send a job application, so the tests care
about two things: that it measures properties the document actually has, and that it never
promises anything about a real applicant tracking system.
"""

from app.models.candidate import ResumeTemplate
from app.schemas.job import JobAnalysis
from app.services.resume.ats import Category, assess
from app.services.resume.rendering import render_html
from tests.test_resume_rendering import DOCUMENT

HTML = render_html(DOCUMENT, ResumeTemplate.STANDARD)


class TestTheScore:
    def test_a_well_formed_resume_scores_well(self) -> None:
        result = assess(DOCUMENT, html=HTML)

        assert 0 <= result.score <= 100
        assert result.score >= 70

    def test_every_category_is_scored_out_of_twenty(self) -> None:
        result = assess(DOCUMENT, html=HTML)

        assert [category.maximum for category in result.categories] == [20] * 5
        assert {category.category for category in result.categories} == set(Category)

    def test_the_total_is_the_sum_of_its_parts(self) -> None:
        result = assess(DOCUMENT, html=HTML)

        assert result.score == sum(category.score for category in result.categories)

    def test_every_category_explains_itself(self) -> None:
        result = assess(DOCUMENT, html=HTML)

        assert all(category.explanation for category in result.categories)

    def test_every_check_says_what_it_found(self) -> None:
        result = assess(DOCUMENT, html=HTML)

        assert result.checks
        assert all(check.detail for check in result.checks)


class TestItNeverOverpromises:
    def test_the_caveat_is_always_present(self) -> None:
        result = assess(DOCUMENT, html=HTML)

        assert "not a universal one" in result.caveat
        assert "different systems" in result.caveat

    def test_nothing_anywhere_guarantees_passing(self) -> None:
        result = assess(DOCUMENT, html=HTML)

        words = " ".join(
            [
                result.caveat,
                *(c.detail for c in result.checks),
                *(c.explanation for c in result.categories),
            ]
        ).lower()
        for forbidden in ("guarantee", "guaranteed to pass", "will pass", "ats-proof"):
            assert forbidden not in words


class TestChecksReactToTheDocument:
    def test_a_resume_with_no_contact_details_loses_structure_points(self) -> None:
        stripped = DOCUMENT.model_copy(
            update={"basics": DOCUMENT.basics.model_copy(update={"email": None, "phone": None})}
        )

        result = assess(stripped, html=HTML)

        contact = next(c for c in result.checks if c.name == "Contact details")
        assert not contact.passed
        structure = next(c for c in result.categories if c.category is Category.STRUCTURE)
        assert structure.score < 20

    def test_a_document_with_a_table_loses_formatting_points(self) -> None:
        result = assess(DOCUMENT, html=HTML.replace("<main", "<table></table><main"))

        formatting = next(c for c in result.categories if c.category is Category.FORMATTING)
        assert formatting.score < 20
        assert "No tables" in formatting.explanation

    def test_an_image_fails_text_extraction(self) -> None:
        result = assess(DOCUMENT, html=HTML.replace("<main", '<img src="x.png" /><main'))

        images = next(c for c in result.checks if c.name == "No text inside images")
        assert not images.passed

    def test_a_pdf_whose_text_cannot_be_read_fails(self) -> None:
        result = assess(DOCUMENT, html=HTML, pdf_text="")

        extraction = next(c for c in result.checks if c.name == "PDF text extractability")
        assert not extraction.passed

    def test_a_pdf_whose_text_matches_passes(self) -> None:
        text = " ".join(
            [
                DOCUMENT.basics.full_name,
                *(b.text for role in DOCUMENT.experience for b in role.bullets),
            ]
        )

        result = assess(DOCUMENT, html=HTML, pdf_text=text)

        extraction = next(c for c in result.checks if c.name == "PDF text extractability")
        assert extraction.passed

    def test_duplicate_lines_are_reported(self) -> None:
        role = DOCUMENT.experience[0]
        doubled = DOCUMENT.model_copy(
            update={
                "experience": [role.model_copy(update={"bullets": [*role.bullets, *role.bullets]})]
            }
        )

        result = assess(doubled, html=HTML)

        duplicates = next(c for c in result.checks if c.name == "No duplicate lines")
        assert not duplicates.passed


class TestKeywordAlignment:
    def test_without_a_job_it_says_so_rather_than_scoring_blind(self) -> None:
        result = assess(DOCUMENT, html=HTML)

        keywords = next(c for c in result.checks if c.name == "Keyword coverage")
        assert keywords.passed
        assert "No job attached" in keywords.detail

    def test_with_a_job_it_counts_what_actually_appears(self) -> None:
        analysis = JobAnalysis(required_skills=["Python", "Kubernetes"], keywords=["payouts"])

        result = assess(DOCUMENT, html=HTML, analysis=analysis)

        coverage = next(c for c in result.checks if c.name == "Keyword coverage")
        assert "of 3" in coverage.detail

    def test_it_tells_the_user_not_to_add_what_is_not_true(self) -> None:
        analysis = JobAnalysis(required_skills=["Kubernetes"])

        result = assess(DOCUMENT, html=HTML, analysis=analysis)

        coverage = next(c for c in result.checks if c.name == "Keyword coverage")
        assert "only add a missing one if it is true" in coverage.detail.lower()
