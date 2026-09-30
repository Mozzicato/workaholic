"""What we tell somebody their record is missing.

This is the coaching half of the product: the writer makes their sentences read well, and this
says the things good writing cannot fix — no project, no course, a grade that invites a no, a
year of work with no number in it. It advises; it never refuses.
"""

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.services.resume.advice import Action, Severity, advise, grade_reading
from tests.conftest import AppFactory, FakeIdentityProvider, bearer, running

ADVICE = "/api/v1/profile/advice"


def record(**sections: Any) -> SimpleNamespace:
    empty: dict[str, Any] = {
        "basics": {"full_name": "Ifeoma Chukwu", "email": "ifeoma@example.com"},
        "experience": [],
        "education": [],
        "projects": [],
        "skills": [],
        "links": {},
    }
    return SimpleNamespace(**{**empty, **sections})


def keys(profile: SimpleNamespace, **kwargs: Any) -> list[str]:
    return [item.key for item in advise(profile, **kwargs)]


GOOD_ROLE = {
    "id": "r1",
    "employer": "Andela",
    "title": "Frontend Intern",
    "bullets": ["rebuilt the reports page, 40 staff use it every day"],
    "technologies": ["React"],
}
GOOD_PROJECT = {
    "id": "p1",
    "name": "Lecture Reminder Bot",
    "description": "sends 60 students their timetable each morning",
    "technologies": ["Python"],
}
FOUR_SKILLS = [{"name": name} for name in ("React", "Python", "SQL", "Git")]


class TestTheHardTruths:
    def test_an_empty_record_is_told_plainly_that_it_will_not_get_a_job(self) -> None:
        """A beginner with nothing to show is better off hearing it here than from silence."""
        found = advise(record())

        worst = found[0]
        assert worst.key == "nothing-done"
        assert worst.severity is Severity.CRITICAL
        assert worst.action is Action.BUILD
        assert "GitHub" in worst.todo

    def test_experience_without_a_project_is_still_told_to_build_one(self) -> None:
        assert "no-projects" in keys(record(experience=[GOOD_ROLE], skills=FOUR_SKILLS))

    def test_projects_without_a_job_are_not_treated_as_a_failure(self) -> None:
        """A student with no job has not done anything wrong, and should not be told they have."""
        found = advise(record(projects=[GOOD_PROJECT], skills=FOUR_SKILLS))

        no_experience = next(item for item in found if item.key == "no-experience")
        assert no_experience.severity is Severity.POLISH
        assert not [item for item in found if item.severity is Severity.CRITICAL]

    def test_a_role_with_nothing_under_it_is_the_worst_thing_on_a_resume(self) -> None:
        bare = {"id": "r1", "employer": "Andela", "title": "Intern", "bullets": []}

        found = advise(record(experience=[bare], projects=[GOOD_PROJECT]))

        empty = next(item for item in found if item.key.startswith("empty-"))
        assert empty.severity is Severity.CRITICAL
        assert empty.item_id == "r1"
        assert "Intern at Andela" in empty.title


class TestNumbers:
    def test_work_with_no_number_anywhere_is_flagged_for_questions(self) -> None:
        role = {**GOOD_ROLE, "bullets": ["i fixed bugs in the internal staff dashboard"]}

        found = advise(record(experience=[role], projects=[GOOD_PROJECT], skills=FOUR_SKILLS))

        unmeasured = next(item for item in found if item.key.startswith("unmeasured-"))
        assert unmeasured.action is Action.ANSWER  # they have the answer; they were never asked
        assert unmeasured.item_id == "r1"

    def test_work_that_already_has_a_number_is_left_alone(self) -> None:
        found = keys(record(experience=[GOOD_ROLE], projects=[GOOD_PROJECT], skills=FOUR_SKILLS))

        assert not [key for key in found if key.startswith("unmeasured-")]

    def test_lines_that_only_ever_say_helped(self) -> None:
        role = {**GOOD_ROLE, "bullets": ["helped with the reports page, about 40 staff used it"]}

        found = advise(record(experience=[role], skills=FOUR_SKILLS))

        assert any(item.key.startswith("vague-") for item in found)


class TestGrades:
    @pytest.mark.parametrize(
        ("grade", "hurts"),
        [
            ("4.31/5", False),
            ("3.8/5", False),
            ("3.4/5", True),
            ("2.9/5", True),
            ("3.6/4", False),
            ("2.8/4", True),
            ("First Class", False),
            ("Second Class Upper", False),
            ("Second Class Lower", True),
            ("2:2", True),
            ("Third Class", True),
            ("72%", False),
            ("48%", True),
        ],
    )
    def test_how_a_grade_reads_to_a_screener(self, grade: str, hurts: bool) -> None:
        assert grade_reading(grade)[1] is hurts

    def test_a_low_grade_is_advised_off_the_page_rather_than_hidden(self) -> None:
        """Leaving a grade off is normal. Deleting it behind their back would not be."""
        school = {"id": "s1", "institution": "Unilag", "qualification": "BSc", "grade": "2.9/5"}

        found = advise(record(education=[school], projects=[GOOD_PROJECT], skills=FOUR_SKILLS))

        advice = next(item for item in found if item.key.startswith("low-grade"))
        assert advice.action is Action.REMOVE
        assert "2.9/5" in advice.title
        assert advice.item_id == "s1"

    def test_a_good_grade_is_never_mentioned(self) -> None:
        school = {"id": "s1", "institution": "Unilag", "qualification": "BSc", "grade": "4.31/5"}

        assert not [
            key
            for key in keys(record(education=[school], projects=[GOOD_PROJECT]))
            if key.startswith("low-grade")
        ]


class TestTheRest:
    def test_a_school_with_no_course_matters_for_a_student(self) -> None:
        school = {"id": "s1", "institution": "University of Lagos"}

        found = advise(record(education=[school], projects=[GOOD_PROJECT]))

        course = next(item for item in found if item.key.startswith("no-course"))
        assert course.severity is Severity.IMPORTANT
        assert "University of Lagos" in course.title

    def test_tools_used_at_work_but_missing_from_skills(self) -> None:
        found = advise(
            record(
                experience=[GOOD_ROLE],
                projects=[GOOD_PROJECT],
                skills=[{"name": "SQL"}, {"name": "Git"}, {"name": "Figma"}, {"name": "Excel"}],
            )
        )

        tools = next(item for item in found if item.key == "tools-not-in-skills")
        assert "react" in tools.detail.lower()
        assert "python" in tools.detail.lower()

    def test_no_github_or_linkedin(self) -> None:
        assert "no-links" in keys(record(projects=[GOOD_PROJECT], skills=FOUR_SKILLS))

    def test_the_worst_thing_is_always_first(self) -> None:
        found = advise(record(education=[{"id": "s1", "institution": "Unilag"}]))

        assert [item.severity for item in found] == sorted(item.severity for item in found)


@pytest.mark.usefixtures("db_engine")
class TestTheEndpoint:
    async def test_it_tells_the_signed_in_user_what_to_fix(
        self, make_app: AppFactory, idp: FakeIdentityProvider
    ) -> None:
        async with running(make_app()) as client:
            headers = bearer(idp.token(subject=str(uuid.uuid4()), email="ada@example.com"))
            await client.get("/api/v1/me", headers=headers)
            await client.patch(
                "/api/v1/profile",
                headers=headers,
                json={
                    "basics": {"full_name": "Ada Lovelace", "email": "ada@example.com"},
                    "education": [
                        {"institution": "Unilag", "qualification": "BSc", "grade": "2.8/5"}
                    ],
                    "experience": [
                        {
                            "employer": "Lumen",
                            "title": "Intern",
                            "bullets": ["i fixed bugs in the dashboard"],
                        }
                    ],
                },
            )

            response = await client.get(ADVICE, headers=headers)

        assert response.status_code == 200
        body = response.json()
        keys_returned = [item["key"] for item in body["items"]]
        assert "no-projects" in keys_returned
        assert any(key.startswith("low-grade") for key in keys_returned)
        assert any(key.startswith("unmeasured-") for key in keys_returned)
        assert body["important"] >= 3
        assert body["items"][0]["severity"] <= body["items"][-1]["severity"]

    async def test_advice_needs_signing_in(self, make_app: AppFactory) -> None:
        async with running(make_app()) as client:
            response = await client.get(ADVICE)

        assert response.status_code == 401
