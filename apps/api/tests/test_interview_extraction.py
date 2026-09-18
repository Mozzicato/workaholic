"""What survives between an answer and the record.

An interview is where facts enter Workaholic, so this is where a fabrication would do the most
damage: anything stored here is treated as the user's own statement for every resume afterwards.
"""

from typing import Any

import pytest

from app.services.interview.extraction import ExtractedFacts, ground

EMPTY: dict[str, Any] = {
    "usable": True,
    "employer": "",
    "title": "",
    "start_date": "",
    "end_date": "",
    "is_current": False,
    "project_name": "",
    "description": "",
    "bullets": [],
    "outcomes": [],
    "technologies": [],
    "skills": [],
    "institution": "",
    "qualification": "",
    "field_of_study": "",
    "certification_name": "",
}


def extraction(**fields: Any) -> ExtractedFacts:
    return ExtractedFacts(**{**EMPTY, **fields})


class TestWhatIsKept:
    def test_the_answer_s_own_words(self) -> None:
        answer = "I interned at Lumen Freight as a backend engineer"

        facts = ground(extraction(employer="Lumen Freight", title="backend engineer"), answer)

        assert facts.employer == "Lumen Freight"
        assert facts.title == "backend engineer"
        assert facts.dropped == []

    def test_a_tidied_sentence(self) -> None:
        answer = "i fixed the invoice import job, it kept failing on big files"

        facts = ground(
            extraction(bullets=["Fixed the invoice import job that kept failing on big files"]),
            answer,
        )

        assert facts.bullets == ["Fixed the invoice import job that kept failing on big files"]

    def test_numbers_the_answer_gives(self) -> None:
        answer = "about 40 students used it in the first week"

        facts = ground(extraction(outcomes=["40 students used it in the first week"]), answer)

        assert facts.outcomes == ["40 students used it in the first week"]

    def test_tools_the_answer_names(self) -> None:
        answer = "it was Python and PostgreSQL, with Docker for local runs"

        facts = ground(extraction(technologies=["Python", "PostgreSQL", "Docker"]), answer)

        assert facts.technologies == ["Python", "PostgreSQL", "Docker"]


class TestWhatIsDropped:
    def test_an_employer_the_answer_never_named(self) -> None:
        facts = ground(extraction(employer="Google"), "I did an internship last summer")

        assert facts.employer == ""
        assert facts.dropped == ["Google"]

    def test_a_number_that_was_not_given(self) -> None:
        facts = ground(
            extraction(outcomes=["cut processing time by 60%"]), "it made the job stop failing"
        )

        assert facts.outcomes == []
        assert facts.dropped == ["cut processing time by 60%"]

    def test_a_tool_that_was_not_named(self) -> None:
        facts = ground(extraction(technologies=["Kubernetes"]), "we deployed it with Docker")

        assert facts.technologies == []

    def test_a_promotion_the_answer_does_not_support(self) -> None:
        facts = ground(extraction(bullets=["Led the migration"]), "i helped with the migration")

        assert facts.bullets == []
        assert facts.dropped == ["Led the migration"]

    def test_one_bad_field_does_not_take_the_good_ones_with_it(self) -> None:
        answer = "I interned at Lumen Freight and wrote tests for the pricing module"

        facts = ground(
            extraction(
                employer="Lumen Freight",
                bullets=["Wrote tests for the pricing module", "Owned the release process"],
            ),
            answer,
        )

        assert facts.employer == "Lumen Freight"
        assert facts.bullets == ["Wrote tests for the pricing module"]
        assert facts.dropped == ["Owned the release process"]


class TestDates:
    def test_a_year_the_answer_states(self) -> None:
        facts = ground(extraction(start_date="2025"), "I started there in 2025")

        assert facts.start_date == "2025"

    def test_a_named_month_may_become_a_number(self) -> None:
        facts = ground(extraction(start_date="2025-06"), "I started in June 2025")

        assert facts.start_date == "2025-06"

    def test_an_abbreviated_month_counts_too(self) -> None:
        facts = ground(extraction(start_date="2025-09"), "started Sept 2025")

        assert facts.start_date == "2025-09"

    def test_a_month_from_nowhere_falls_back_to_the_year(self) -> None:
        facts = ground(extraction(start_date="2025-03"), "I was there during 2025")

        assert facts.start_date == "2025"
        assert "2025-03" in facts.dropped

    def test_a_year_from_nowhere_is_dropped(self) -> None:
        facts = ground(extraction(start_date="2019"), "I was there for a summer")

        assert facts.start_date == ""

    def test_a_current_role_keeps_no_end_date(self) -> None:
        facts = ground(
            extraction(is_current=True, start_date="2025", end_date="2026"),
            "I started in 2025 and I am still there, it is 2026 now",
        )

        assert facts.is_current is True
        assert facts.end_date == ""


class TestUsability:
    @pytest.mark.parametrize("answer", ["I don't know", "skip", "what do you mean?"])
    def test_an_answer_with_no_facts_records_nothing(self, answer: str) -> None:
        facts = ground(extraction(usable=False), answer)

        assert facts.usable is False
        assert facts.is_empty

    def test_an_answer_with_facts_is_not_empty(self) -> None:
        facts = ground(extraction(skills=["Python"]), "I am comfortable with Python")

        assert not facts.is_empty
