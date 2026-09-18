"""Choosing what to ask about.

This is deliberately model-free: the subject of every question is decided from the record, so
these tests pin the interview's behaviour without a model in sight.
"""

from typing import Any

from app.services.interview.gaps import Topic, next_gap, open_gaps

KNOWN_BASICS = {"full_name": "Ada Lovelace", "email": "ada@lovelace.dev"}
KNOWN_SCHOOL = [{"id": "s1", "institution": "Unilag", "grade": "4.5/5"}]


class Profile:
    """Just enough of a candidate profile for the gap rules.

    Name, contact and school default to known, so tests about work start where the work does.
    """

    def __init__(self, **sections: Any) -> None:
        self.basics = sections.get("basics", KNOWN_BASICS)
        self.education = sections.get("education", KNOWN_SCHOOL)
        for name in ("experience", "projects", "skills", "certifications"):
            setattr(self, name, sections.get(name, []))


NOBODY_YET: dict[str, Any] = {"basics": {}, "education": []}


ROLE = {
    "id": "role-1",
    "employer": "Lumen Freight",
    "title": "Backend Engineer Intern",
    "bullets": ["fixed the invoice import job so it stopped failing"],
    "technologies": ["Python"],
}


class TestPriority:
    def test_an_empty_record_starts_with_their_name(self) -> None:
        gap = next_gap(Profile(**NOBODY_YET))

        assert gap is not None
        assert gap.topic is Topic.NAME

    def test_it_walks_through_who_they_are_before_what_they_did(self) -> None:
        """Name, contact, school, grade, then work: the order a person fills a resume in."""
        topics = [gap.topic for gap in open_gaps(Profile(**NOBODY_YET))]

        assert topics[:4] == [Topic.NAME, Topic.CONTACT, Topic.EDUCATION, Topic.EXPERIENCE]

    def test_a_school_without_a_grade_is_asked_about_before_work(self) -> None:
        gaps = open_gaps(Profile(education=[{"id": "s1", "institution": "Unilag"}]))

        assert gaps[0].topic is Topic.GRADE
        assert gaps[0].item_id == "s1"
        assert gaps[0].subject == "Unilag"

    def test_a_phone_number_is_contact_enough(self) -> None:
        topics = [
            gap.topic for gap in open_gaps(Profile(basics={"full_name": "Ada", "phone": "0801"}))
        ]

        assert Topic.CONTACT not in topics

    def test_with_the_basics_known_it_starts_with_work_history(self) -> None:
        gap = next_gap(Profile())

        assert gap is not None
        assert gap.topic is Topic.EXPERIENCE

    def test_a_role_with_nothing_said_about_it_comes_next(self) -> None:
        gap = next_gap(Profile(experience=[{"id": "r1", "employer": "Lumen", "title": "Intern"}]))

        assert gap is not None
        assert gap.topic is Topic.EXPERIENCE_DETAIL
        assert gap.subject == "Intern at Lumen"

    def test_duties_without_a_result_are_asked_about_before_tools(self) -> None:
        role = {**ROLE, "bullets": ["wrote tests for the pricing module"], "technologies": []}

        topics = [gap.topic for gap in open_gaps(Profile(experience=[role]))]

        assert topics.index(Topic.EXPERIENCE_OUTCOME) < topics.index(Topic.TECHNOLOGIES)

    def test_experience_is_asked_about_before_projects(self) -> None:
        topics = [gap.topic for gap in open_gaps(Profile())]

        assert topics.index(Topic.EXPERIENCE) < topics.index(Topic.PROJECTS)

    def test_certifications_come_last(self) -> None:
        topics = [gap.topic for gap in open_gaps(Profile())]

        assert topics[-1] is Topic.CERTIFICATIONS


class TestWhatCountsAsFilled:
    def test_a_bullet_with_a_number_counts_as_an_outcome(self) -> None:
        role = {**ROLE, "bullets": ["cut the import time from 40 minutes to 5"]}

        topics = [gap.topic for gap in open_gaps(Profile(experience=[role]))]

        assert Topic.EXPERIENCE_OUTCOME not in topics

    def test_a_bullet_that_reports_a_change_counts_as_an_outcome(self) -> None:
        role = {**ROLE, "bullets": ["stopped the nightly job from failing"]}

        topics = [gap.topic for gap in open_gaps(Profile(experience=[role]))]

        assert Topic.EXPERIENCE_OUTCOME not in topics

    def test_a_duty_alone_does_not(self) -> None:
        role = {**ROLE, "bullets": ["responsible for the pricing module"]}

        topics = [gap.topic for gap in open_gaps(Profile(experience=[role]))]

        assert Topic.EXPERIENCE_OUTCOME in topics

    def test_recorded_tools_close_the_tools_gap(self) -> None:
        gaps = open_gaps(Profile(experience=[ROLE]))

        assert not [gap for gap in gaps if gap.topic is Topic.TECHNOLOGIES]

    def test_a_named_project_with_nothing_else_is_asked_about(self) -> None:
        gap = next_gap(Profile(experience=[ROLE], projects=[{"id": "p1", "name": "Bus tracker"}]))

        assert gap is not None
        assert gap.topic is Topic.PROJECT_DETAIL
        assert gap.subject == "Bus tracker"


class TestNotRepeatingYourself:
    def test_a_gap_already_asked_about_is_skipped(self) -> None:
        profile = Profile()
        first = next_gap(profile)
        assert first is not None

        second = next_gap(profile, asked=[first.key])

        assert second is not None
        assert second.key != first.key

    def test_the_interview_ends_when_nothing_is_left(self) -> None:
        profile = Profile(
            experience=[{**ROLE, "bullets": ["cut import failures to zero"]}],
            projects=[
                {
                    "id": "p1",
                    "name": "Bus tracker",
                    "description": "shows the shuttle",
                    "outcomes": ["40 students used it"],
                    "technologies": ["TypeScript"],
                }
            ],
            skills=[{"name": "Python"}],
            education=[{"institution": "Unilag", "grade": "Second Class Upper"}],
            certifications=[{"name": "AZ-900"}],
        )

        assert next_gap(profile) is None

    def test_every_gap_carries_a_stable_key(self) -> None:
        gaps = open_gaps(Profile(experience=[{"id": "r1", "employer": "Lumen", "title": "Intern"}]))

        keys = [gap.key for gap in gaps]
        assert len(keys) == len(set(keys))
        assert all(":" in key for key in keys)


class TestRobustness:
    def test_a_record_full_of_junk_does_not_crash_the_interview(self) -> None:
        profile = Profile(experience=["not a dict", None, {"bullets": "not a list"}])

        gaps = open_gaps(profile)

        assert all(gap.subject for gap in gaps)

    def test_an_item_without_an_id_is_still_addressable(self) -> None:
        gap = next_gap(Profile(experience=[{"employer": "Lumen", "title": "Intern"}]))

        assert gap is not None
        assert gap.item_id == "index-0"
