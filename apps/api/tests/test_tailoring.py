"""Tailoring (PRD §33).

Tailoring is the feature most likely to be asked to cheat: a job wants Kubernetes, the candidate
has none, and the obvious "helpful" move is to make the resume say otherwise. This module cannot
do that — it only reorders — and these tests hold it to that.
"""

from app.schemas.job import JobAnalysis, MatchState, RequirementMatch
from app.schemas.resume_document import (
    Bullet,
    ResumeBasics,
    ResumeDocument,
    ResumeExperience,
    ResumeProject,
    ResumeSkillGroup,
)
from app.services.resume.tailoring import tailor


def bullet(text: str, item_id: str = "role-1", index: int = 0) -> Bullet:
    return Bullet(text=text, source_item_id=item_id, source_bullet_index=index)


DOCUMENT = ResumeDocument(
    basics=ResumeBasics(full_name="Ada Lovelace", email="ada@example.com"),
    experience=[
        ResumeExperience(
            item_id="role-1",
            employer="Campus Cafe",
            title="Barista",
            start_date="2024-01",
            bullets=[bullet("Served customers during the morning rush", "role-1", 0)],
        ),
        ResumeExperience(
            item_id="role-2",
            employer="Lumen Freight",
            title="Backend Engineer Intern",
            start_date="2025-06",
            bullets=[
                bullet("Wrote the deployment notes for the team", "role-2", 0),
                bullet("Changed the invoice import job to read files in chunks", "role-2", 1),
            ],
            technologies=["Python", "PostgreSQL"],
        ),
    ],
    projects=[
        ResumeProject(item_id="project-1", name="Bus tracker", technologies=["TypeScript"]),
    ],
    skills=[ResumeSkillGroup(category="Languages", skills=["TypeScript", "Python"])],
)

ANALYSIS = JobAnalysis(
    required_skills=["Python", "PostgreSQL"],
    keywords=["invoice", "import"],
)

MISSING = [
    RequirementMatch(
        requirement="Kubernetes",
        state=MatchState.NOT_FOUND,
        kind="required",
        evidence=[],
        explanation="Your record doesn't mention this.",
    )
]


class TestEmphasis:
    def test_the_relevant_role_comes_first(self) -> None:
        result = tailor(DOCUMENT, ANALYSIS, [])

        assert [role.item_id for role in result.document.experience] == ["role-2", "role-1"]
        assert any("Reordered your roles" in note for note in result.changed)

    def test_the_relevant_line_leads_within_a_role(self) -> None:
        result = tailor(DOCUMENT, ANALYSIS, [])

        role = next(r for r in result.document.experience if r.item_id == "role-2")
        assert role.bullets[0].text.startswith("Changed the invoice import job")

    def test_the_skills_the_job_named_come_first(self) -> None:
        result = tailor(DOCUMENT, ANALYSIS, [])

        assert result.document.skills[0].skills == ["Python", "TypeScript"]

    def test_it_says_what_it_moved(self) -> None:
        result = tailor(DOCUMENT, ANALYSIS, [])

        assert result.changed
        assert all(isinstance(note, str) and note for note in result.changed)


class TestWhatItCannotDo:
    def test_no_wording_changes(self) -> None:
        result = tailor(DOCUMENT, ANALYSIS, [])

        before = {b.text for role in DOCUMENT.experience for b in role.bullets}
        after = {b.text for role in result.document.experience for b in role.bullets}
        assert before == after

    def test_nothing_is_added_or_removed(self) -> None:
        result = tailor(DOCUMENT, ANALYSIS, MISSING)

        assert len(result.document.experience) == len(DOCUMENT.experience)
        assert len(result.document.projects) == len(DOCUMENT.projects)
        before = {skill for group in DOCUMENT.skills for skill in group.skills}
        after = {skill for group in result.document.skills for skill in group.skills}
        assert before == after

    def test_a_missing_requirement_is_reported_not_filled(self) -> None:
        result = tailor(DOCUMENT, ANALYSIS, MISSING)

        assert result.missing_requirements == ["Kubernetes"]
        text = " ".join(b.text for role in result.document.experience for b in role.bullets).lower()
        assert "kubernetes" not in text

    def test_employers_titles_and_dates_are_untouched(self) -> None:
        result = tailor(DOCUMENT, ANALYSIS, [])

        originals = {role.item_id: role for role in DOCUMENT.experience}
        for role in result.document.experience:
            original = originals[role.item_id]
            assert (role.employer, role.title, role.start_date, role.end_date) == (
                original.employer,
                original.title,
                original.start_date,
                original.end_date,
            )

    def test_it_states_plainly_what_it_never_touches(self) -> None:
        result = tailor(DOCUMENT, ANALYSIS, [])

        stated = " ".join(result.unchanged).lower()
        assert "employers" in stated
        assert "wording" in stated


class TestEdges:
    def test_an_unanalysed_job_changes_nothing(self) -> None:
        result = tailor(DOCUMENT, JobAnalysis(), [])

        assert [role.item_id for role in result.document.experience] == ["role-1", "role-2"]
        assert result.changed == []

    def test_a_document_already_in_the_right_order_reports_no_change(self) -> None:
        once = tailor(DOCUMENT, ANALYSIS, [])

        twice = tailor(once.document, ANALYSIS, [])

        assert twice.changed == []
        assert [r.item_id for r in twice.document.experience] == [
            r.item_id for r in once.document.experience
        ]
