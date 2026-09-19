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

__all__ = ["ExtractedFacts", "GroundedFacts", "grade_stated", "ground"]

_YEAR = re.compile(r"(19|20)\d{2}")
_WORD = re.compile(r"[A-Za-z][A-Za-z0-9'.+#-]*")
# Words that carry no claim of their own, so they need not appear in the answer verbatim.
_JOINING_WORDS = frozenset(
    {"a", "an", "and", "at", "by", "for", "in", "of", "on", "or", "the", "to", "with"}
)
# A whole answer that is a refusal ("none", "n/a"), or a name that opens by declining ("no
# certifications yet", "haven't got one"). "Nothing Phone" and "Nil Studio" are real names, so those
# words count only on their own.
_REFUSAL = re.compile(
    r"(none|nothing|nope|n/?a|nil|no|not yet|never)[.!]?$"
    r"|(no|not|never|haven'?t|have not|don'?t|do not|i don'?t|i haven'?t)\s",
    re.I,
)
_EMAIL = re.compile(r"[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)+")
_SPOKEN_AT = re.compile(r"\s+at\s+")
_SPOKEN_DOT = re.compile(r"\s+dot\s+")
_GRADE_TOKEN = re.compile(r"[A-Za-z]+|\d+(?:\.\d+)?")
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
    full_name: str
    email: str
    phone: str
    location: str
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
    grade: str
    certification_name: str


@dataclass(slots=True)
class GroundedFacts:
    """The parts of an extraction the answer supports."""

    usable: bool = False
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
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
    grade: str = ""
    certification_name: str = ""
    dropped: list[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not any(
            (
                self.full_name,
                self.email,
                self.phone,
                self.location,
                self.grade,
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
        "full_name",
        "location",
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
        if _named_in(value, answer) and not _is_refusal(value):
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
            supported = (
                _named_in(text, answer) and not _is_refusal(text)
                if is_name_list
                else _supported(text, answer)
            )
            if supported:
                kept.append(text)
            else:
                grounded.dropped.append(text)
        setattr(grounded, name, kept)

    grounded.email = _grounded_email(facts.email, answer, grounded)
    grounded.phone = _grounded_phone(facts.phone, answer, grounded)
    grounded.grade = _grounded_grade(facts.grade, answer, grounded)

    grounded.start_date = _grounded_date(facts.start_date, answer, grounded)
    grounded.end_date = _grounded_date(facts.end_date, answer, grounded)
    if grounded.is_current:
        grounded.end_date = ""
    return grounded


def _is_refusal(value: str) -> bool:
    """ "no certifications yet" was said, so every word of it is grounded — and it is not a name.

    Found against the live model, which once recorded it as a certification. A name that opens by
    saying there is nothing is a person declining, and it must never reach a resume.
    """
    return bool(_REFUSAL.match(value.strip()))


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


def _grounded_email(value: str, answer: str, grounded: GroundedFacts) -> str:
    """An address is kept only when the answer spells it out, typed or spoken.

    Said aloud, "ada at gmail dot com" is transcribed as words; that is the same address, so the
    answer is read both ways. Anything else — a guessed domain, a completed username — is dropped.
    """
    email = value.strip().lower()
    if not email:
        return ""
    heard = _SPOKEN_AT.sub("@", answer.lower())
    heard = _SPOKEN_DOT.sub(".", heard)
    heard = re.sub(r"\s+", "", heard)
    if _EMAIL.fullmatch(email) and email in heard:
        return email
    grounded.dropped.append(value.strip())
    return ""


def _grounded_phone(value: str, answer: str, grounded: GroundedFacts) -> str:
    """A number is kept only when its digits appear, in order, in what was said."""
    phone = value.strip()
    digits = re.sub(r"\D", "", phone)
    if not phone:
        return ""
    if 7 <= len(digits) <= 15 and digits in re.sub(r"\D", "", answer):
        return phone
    grounded.dropped.append(phone)
    return ""


def _grounded_grade(value: str, answer: str, grounded: GroundedFacts) -> str:
    """A grade is kept only when every part of it was said: "4.52/5" or "Second Class Upper"."""
    grade = value.strip()
    if not grade:
        return ""
    if grade_stated(grade, answer):
        return grade
    grounded.dropped.append(grade)
    return ""


def grade_stated(grade: str, text: str) -> bool:
    """True when every part of this grade appears in the text, so none of it was converted."""
    said = {token.lower() for token in _GRADE_TOKEN.findall(text)}
    parts = [token.lower() for token in _GRADE_TOKEN.findall(grade)]
    return bool(parts) and all(part in said for part in parts)


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
