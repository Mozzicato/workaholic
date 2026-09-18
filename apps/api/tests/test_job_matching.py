"""Matching a job's requirements against the record (PRD §32).

The only wrong answer that really hurts is MATCHED where the record does not support it: it tells
someone they are qualified for something they are not, and invites them to say so.
"""

from typing import Any

from app.schemas.job import JobAnalysis, MatchState
from app.services.job.matching import match_requirements


class Profile:
    def __init__(self, **sections: Any) -> None:
        self.basics = sections.get("basics", {})
        for name in ("experience", "projects", "skills"):
            setattr(self, name, sections.get(name, []))


RECORD = Profile(
    skills=[{"name": "Python"}, {"name": "PostgreSQL"}],
    experience=[
        {
            "employer": "Lumen Freight",
            "title": "Backend Engineer Intern",
            "bullets": [
                "changed the invoice import job to read files in chunks",
                "wrote the deployment steps in the README, we deployed with Docker",
            ],
            "technologies": ["Python", "PostgreSQL"],
        }
    ],
    projects=[
        {"name": "Bus tracker", "outcomes": ["40 students used it"], "technologies": ["TypeScript"]}
    ],
)


def verdicts(*required: str, preferred: tuple[str, ...] = ()) -> dict[str, MatchState]:
    analysis = JobAnalysis(required_skills=list(required), preferred_skills=list(preferred))
    return {match.requirement: match.state for match in match_requirements(analysis, RECORD)}


class TestMatched:
    def test_a_listed_skill(self) -> None:
        assert verdicts("Python")["Python"] is MatchState.MATCHED

    def test_a_tool_named_on_a_role(self) -> None:
        assert verdicts("PostgreSQL")["PostgreSQL"] is MatchState.MATCHED

    def test_a_tool_named_on_a_project(self) -> None:
        assert verdicts("TypeScript")["TypeScript"] is MatchState.MATCHED

    def test_an_alias_the_advert_happens_to_use(self) -> None:
        assert verdicts("Postgres")["Postgres"] is MatchState.MATCHED

    def test_case_does_not_matter(self) -> None:
        assert verdicts("python")["python"] is MatchState.MATCHED


class TestPartiallyMatched:
    def test_something_mentioned_in_the_work_but_never_claimed(self) -> None:
        """Docker appears in a sentence about what they did, but is not a listed skill."""
        assert verdicts("Docker")["Docker"] is MatchState.PARTIALLY_MATCHED

    def test_it_says_where_it_saw_it(self) -> None:
        analysis = JobAnalysis(required_skills=["Docker"])

        match = match_requirements(analysis, RECORD)[0]

        assert match.evidence == [
            "wrote the deployment steps in the README, we deployed with Docker"
        ]
        assert "haven't listed it as a skill" in match.explanation


class TestNotFound:
    def test_a_skill_the_record_never_mentions(self) -> None:
        assert verdicts("Kubernetes")["Kubernetes"] is MatchState.NOT_FOUND

    def test_it_promises_not_to_fill_the_gap(self) -> None:
        analysis = JobAnalysis(required_skills=["Kubernetes"])

        match = match_requirements(analysis, RECORD)[0]

        assert match.evidence == []
        assert "Nothing will be added for you" in match.explanation

    def test_a_substring_of_a_real_word_is_not_a_match(self) -> None:
        """ "Go" must not match "Django", and "R" must not match every sentence."""
        assert verdicts("Go")["Go"] is MatchState.NOT_FOUND
        assert verdicts("R")["R"] is MatchState.NOT_FOUND

    def test_an_empty_record_matches_nothing(self) -> None:
        analysis = JobAnalysis(required_skills=["Python", "Docker"])

        matches = match_requirements(analysis, Profile())

        assert {match.state for match in matches} == {MatchState.NOT_FOUND}


class TestTheReport:
    def test_required_and_preferred_are_both_reported_and_labelled(self) -> None:
        analysis = JobAnalysis(required_skills=["Python"], preferred_skills=["Docker"])

        matches = match_requirements(analysis, RECORD)

        assert [match.kind for match in matches] == ["required", "preferred"]

    def test_a_requirement_listed_twice_is_reported_once(self) -> None:
        analysis = JobAnalysis(required_skills=["Python"], preferred_skills=["python"])

        matches = match_requirements(analysis, RECORD)

        assert len(matches) == 1

    def test_the_advert_s_order_is_kept(self) -> None:
        analysis = JobAnalysis(required_skills=["Kubernetes", "Python", "Docker"])

        matches = match_requirements(analysis, RECORD)

        assert [match.requirement for match in matches] == ["Kubernetes", "Python", "Docker"]

    def test_an_unanalysed_advert_reports_nothing_rather_than_failing(self) -> None:
        assert match_requirements(JobAnalysis(), RECORD) == []
