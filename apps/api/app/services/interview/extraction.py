"""What the model may return from an answer, and what survives checking.

`ExtractedFacts` is the shape the model fills in. `ground` then compares every field against what
the person actually said and returns only the supported parts. The same deterministic checks that
guard resume wording guard this: a fact that enters the record here becomes a claim on a resume
later, so it has to be the person's, not the model's.
"""

import re
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict

from app.services.resume.validation import check_text, vocabulary_of

__all__ = ["ExtractedFacts", "GroundedFacts", "ground"]

_YEAR = re.compile(r"(19|20)\d{2}")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9'.+#-]*")
# Words that carry no claim of their own, so they need not appear in the answer verbatim.
_JOINING_WORDS = frozenset(
    {"a", "an", "and", "at", "by", "for", "in", "of", "on", "or", "the", "to", "with"}
)
_MONTH_NAMES = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)


class ExtractedFacts(BaseModel):
    """One flat record. Every field is required so the schema stays strict; empty means absent."""

    model_config = ConfigDict(extra="forbid")

    usable: bool
    employer: str
    title: str
    start_date: str
    end_date: str
    is_current: bool
    project_name: str
    description: str
    bullets: list[str]
    outcomes: list[str]
    technologies: list[str]
    skills: list[str]
    institution: str
    qualification: str
    field_of_study: str
    certification_name: str


@dataclass(slots=True)
class GroundedFacts:
    """The parts of an extraction the answer supports."""

    usable: bool = False
    employer: str = ""
    title: str = ""
    start_date: str = ""
    end_date: str = ""
    is_current: bool = False
    project_name: str = ""
    description: str = ""
    bullets: list[str] = field(default_factory=list)
    outcomes: list[str] = field(default_factory=list)
    technologies: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    institution: str = ""
    qualification: str = ""
    field_of_study: str = ""
    certification_name: str = ""
    dropped: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not any(
            (
                self.employer,
                self.title,
                self.project_name,
                self.description,
                self.bullets,
                self.outcomes,
                self.technologies,
                self.skills,
                self.institution,
                self.qualification,
                self.certification_name,
            )
        )


def ground(facts: ExtractedFacts, answer: str) -> GroundedFacts:
    """Keep what the answer supports; drop the rest and say what was dropped."""
    grounded = GroundedFacts(usable=facts.usable, is_current=facts.is_current)

    # Names are checked word by word: "Google" on its own is capitalised like any first word,
    # so only membership in what the person said can tell an employer from an invention.
    for name in (
        "employer",
        "title",
        "project_name",
        "institution",
        "qualification",
        "field_of_study",
        "certification_name",
    ):
        value = getattr(facts, name).strip()
        if not value:
            continue
        if _named_in(value, answer):
            setattr(grounded, name, value)
        else:
            grounded.dropped.append(value)

    if facts.description.strip():
        if _supported(facts.description.strip(), answer):
            grounded.description = facts.description.strip()
        else:
            grounded.dropped.append(facts.description.strip())

    for name, is_name_list in (
        ("bullets", False),
        ("outcomes", False),
        ("technologies", True),
        ("skills", True),
    ):
        kept: list[str] = []
        for value in getattr(facts, name):
            text = value.strip()
            if not text:
                continue
            supported = _named_in(text, answer) if is_name_list else _supported(text, answer)
            if supported:
                kept.append(text)
            else:
                grounded.dropped.append(text)
        setattr(grounded, name, kept)

    grounded.start_date = _grounded_date(facts.start_date, answer, grounded)
    grounded.end_date = _grounded_date(facts.end_date, answer, grounded)
    if grounded.is_current:
        grounded.end_date = ""
    return grounded


def _supported(value: str, answer: str) -> bool:
    """True when nothing in this sentence goes beyond what the answer says."""
    return not check_text(location="answer", rewritten=value, sources=[answer])


def _named_in(value: str, answer: str) -> bool:
    """True when every meaningful word of this name appears in the answer."""
    known = vocabulary_of([answer])
    words = [
        word
        for match in _WORD.finditer(value)
        if (word := match.group(0).lower().strip(".")) not in _JOINING_WORDS
    ]
    if not words:
        return False
    return all(word in known for word in words) and _supported(value, answer)


def _grounded_date(value: str, answer: str, grounded: GroundedFacts) -> str:
    """A date is kept only when its year is in the answer, and its month is too if it has one.

    "March 2024" becoming "2024-03" is a legitimate reformatting, so months are matched by name
    as well as by number — but a month that appears from nowhere is dropped.
    """
    date = value.strip()
    if not date:
        return ""
    year, _, month = date.partition("-")
    if not _YEAR.fullmatch(year) or year not in answer:
        grounded.dropped.append(date)
        return ""
    if not month:
        return year
    index = int(month) if month.isdigit() and 1 <= int(month) <= 12 else 0
    if index == 0:
        grounded.dropped.append(date)
        return year
    named = _MONTH_NAMES[index - 1]
    lowered = answer.lower()
    if named in lowered or named[:3] in lowered or f"-{month}" in answer or f"/{month}" in answer:
        return f"{year}-{month}"
    grounded.dropped.append(date)
    return year
