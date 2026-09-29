"""What the record is still missing (PRD §23.1, §24).

Choosing the subject of the next question is a decision about the user's data, so code makes it,
not the model. The model is given one gap and asked to phrase a question about it. That keeps the
interview predictable, keeps it testable without a model, and stops it drifting into small talk.

The order of `Topic` is the order a person would be walked through building a resume: who you
are and how to reach you, where you studied, then what you have done — experience before
projects, what you did before what you used. Within the work, it keeps the priority order in PRD
§24. A gap for an item the user has already been asked about is skipped, so the interview moves
on instead of nagging.

The last topics are different in kind. Once the record holds everything a resume needs, the
questions turn to *impact*: how many, how often, what it was like before, who ended up using it.
Most people have those answers and never think to give them — and that is exactly the difference
between "helped with the invoice job" and a bullet that gets an interview. Asking is the only
honest way to get them.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

__all__ = ["Gap", "Topic", "next_gap", "open_gaps"]

# A number, or a word that reports a result. Used to tell "what I did" from "what changed".
_OUTCOME_SIGNALS = re.compile(
    r"\d|\b(reduced|cut|saved|increased|grew|improved|faster|slower|fixed|stopped|"
    r"shipped|launched|adopted|used by|replaced|removed|halved|doubled)\b",
    re.I,
)


class Topic(IntEnum):
    """Subjects an interview can cover, most valuable first."""

    NAME = 1  # no name to put at the top of the page
    CONTACT = 2  # no email address or phone number
    EDUCATION = 3  # no school or course recorded
    GRADE = 4  # a school with no grade — optional, and the question says so
    EXPERIENCE = 5  # no roles recorded at all
    EXPERIENCE_DETAIL = 6  # a role with nothing said about it
    EXPERIENCE_OUTCOME = 7  # a role described only as duties, with no result
    TECHNOLOGIES = 8  # a role or project with no tools named
    PROJECTS = 9  # nothing built outside a job
    PROJECT_DETAIL = 10
    PROJECT_OUTCOME = 11
    SKILLS = 12
    CERTIFICATIONS = 13
    # Sharpening, once the record is complete: the facts that make a bullet land.
    IMPACT_SCALE = 14  # nothing says how big, how many or how often
    IMPACT_CHANGE = 15  # something was changed, but not what it was like before
    IMPACT_REACH = 16  # nothing says who ended up using it


@dataclass(frozen=True, slots=True)
class Gap:
    """One thing worth asking about, and enough context to phrase the question."""

    topic: Topic
    item_id: str | None
    subject: str  # what the question is about, in the user's own terms
    missing: str  # what is absent, in plain words, for the model to turn into a question

    @property
    def key(self) -> str:
        """Identifies the gap across turns, so the same one is not asked twice."""
        return f"{self.topic.name.lower()}:{self.item_id or '-'}"


# A number, spelled out or in digits: the thing most student bullets are missing.
_NUMBER = re.compile(r"\d")
_NUMBER_WORDS = re.compile(
    r"\b(zero|none|one|two|three|four|five|six|seven|eight|nine|ten|dozen|hundred|thousand|"
    r"million|once|twice|daily|weekly|monthly|every)\b",
    re.I,
)
# Language that compares a before with an after.
_CHANGE_WORDS = re.compile(
    r"\b(before|previously|used to|instead of|after|from|now|first|no longer|stopped|"
    r"faster|slower|quicker|longer|shorter|less|more|down to|up to)\b",
    re.I,
)
# Work done *to* something that already existed. Asking what a bus tracker was like before it
# was built is a silly question; asking what the import job was like before it was fixed is the
# best question on the page.
_CHANGE_TRIGGER = re.compile(
    r"\b(fix|fixed|fixing|change|changed|rebuil|rewr|refactor|improv|optimis|optimiz|speed|"
    r"sped|reduc|cut|migrat|replac|automat|streamlin|solv|debug|updat|upgrad|clean)\w*\b",
    re.I,
)

# Language that says somebody other than the author touched it.
_REACH_WORDS = re.compile(
    r"\b(used|users|people|students|staff|team|colleagues|customers|clients|downloads|"
    r"installs|visits|signed up|adopted|shared|shipped|released|published|live)\b",
    re.I,
)

MAX_IMPACT_QUESTIONS_PER_ITEM = 2
"""Two per role or project. More than that is an interrogation people abandon."""

MAX_IMPACT_QUESTIONS_PER_CONVERSATION = 6
"""And six in one sitting. There is always another number to ask for; a conversation with no
end is one nobody finishes, and whatever is left keeps until the next one."""


def _impact_gaps(item: dict[str, Any], item_id: str, subject: str, kind: str) -> list[Gap]:
    """What this item does not yet say about its own impact, most valuable first.

    Only for items that already describe something: there is nothing to sharpen about a role
    with no lines under it, and `EXPERIENCE_DETAIL` asks about that first.
    """
    lines = _strings(item.get("bullets")) + _strings(item.get("outcomes"))
    description = _text(item.get("description"))
    if description:
        lines = [description, *lines]
    if not lines:
        return []

    said = " ".join(lines)
    quoted = _quote(lines[0])
    gaps: list[Gap] = []

    if not _NUMBER.search(said) and not _NUMBER_WORDS.search(said):
        gaps.append(
            Gap(
                topic=Topic.IMPACT_SCALE,
                item_id=item_id,
                subject=subject,
                missing=(
                    f"nothing here says how big or how often: they said {quoted}, with no number "
                    "anywhere — how many people, how many times, how much data, how long it took"
                ),
            )
        )
    if _CHANGE_TRIGGER.search(said) and not _CHANGE_WORDS.search(said):
        gaps.append(
            Gap(
                topic=Topic.IMPACT_CHANGE,
                item_id=item_id,
                subject=subject,
                missing=(
                    f"they said {quoted} but not what it was like before they did it, so there is "
                    "nothing to compare the result against"
                ),
            )
        )
    if not _REACH_WORDS.search(said):
        gaps.append(
            Gap(
                topic=Topic.IMPACT_REACH,
                item_id=item_id,
                subject=subject,
                missing=(
                    f"nothing says who ended up using this {kind} or what happened to it "
                    f"afterwards: they said {quoted}"
                ),
            )
        )
    return gaps[:MAX_IMPACT_QUESTIONS_PER_ITEM]


def open_gaps(profile: Any, asked: Sequence[str] = ()) -> list[Gap]:
    """Every gap in this profile, most valuable first, excluding ones already asked about."""
    experience = _items(getattr(profile, "experience", None))
    projects = _items(getattr(profile, "projects", None))
    skills = _items(getattr(profile, "skills", None))
    education = _items(getattr(profile, "education", None))
    certifications = _items(getattr(profile, "certifications", None))
    basics = getattr(profile, "basics", None)
    basics = basics if isinstance(basics, dict) else {}

    gaps: list[Gap] = []

    if not _text(basics.get("full_name")):
        gaps.append(
            Gap(
                topic=Topic.NAME,
                item_id=None,
                subject="their name",
                missing="no name is recorded for the top of the resume",
            )
        )
    if not _text(basics.get("email")) and not _text(basics.get("phone")):
        gaps.append(
            Gap(
                topic=Topic.CONTACT,
                item_id=None,
                subject="how to contact them",
                missing="no email address or phone number is recorded",
            )
        )
    if not education:
        gaps.append(
            Gap(
                topic=Topic.EDUCATION,
                item_id=None,
                subject="their education",
                missing="no school, degree or course is recorded",
            )
        )
    for index, school in enumerate(education):
        if not _text(school.get("grade")):
            gaps.append(
                Gap(
                    topic=Topic.GRADE,
                    item_id=_identifier(school, index),
                    subject=_text(school.get("institution")) or "their course",
                    missing="no grade or CGPA is recorded, and it is optional",
                )
            )

    if not experience:
        gaps.append(
            Gap(
                topic=Topic.EXPERIENCE,
                item_id=None,
                subject="their work history",
                missing="no job, internship or placement has been recorded yet",
            )
        )

    for index, role in enumerate(experience):
        item_id = _identifier(role, index)
        where = _role_label(role)
        bullets = _strings(role.get("bullets"))
        if not bullets:
            gaps.append(
                Gap(
                    topic=Topic.EXPERIENCE_DETAIL,
                    item_id=item_id,
                    subject=where,
                    missing="nothing has been recorded about what they actually did in this role",
                )
            )
            continue
        if not any(_OUTCOME_SIGNALS.search(bullet) for bullet in bullets):
            gaps.append(
                Gap(
                    topic=Topic.EXPERIENCE_OUTCOME,
                    item_id=item_id,
                    subject=where,
                    missing=(
                        "their duties are recorded but not what changed because of them: "
                        f"they said {_quote(bullets[0])}"
                    ),
                )
            )
        if not _strings(role.get("technologies")):
            gaps.append(
                Gap(
                    topic=Topic.TECHNOLOGIES,
                    item_id=item_id,
                    subject=where,
                    missing="no tools, languages or systems are recorded for this role",
                )
            )

    if not projects:
        gaps.append(
            Gap(
                topic=Topic.PROJECTS,
                item_id=None,
                subject="things they have built outside a job",
                missing="no project, coursework or side build has been recorded",
            )
        )

    for index, project in enumerate(projects):
        item_id = _identifier(project, index)
        name = _text(project.get("name")) or "their project"
        outcomes = _strings(project.get("outcomes"))
        if not _text(project.get("description")) and not outcomes:
            gaps.append(
                Gap(
                    topic=Topic.PROJECT_DETAIL,
                    item_id=item_id,
                    subject=name,
                    missing="the project is named but nothing describes what it is or does",
                )
            )
            continue
        if not outcomes:
            gaps.append(
                Gap(
                    topic=Topic.PROJECT_OUTCOME,
                    item_id=item_id,
                    subject=name,
                    missing="nothing records whether anyone used it or what came of it",
                )
            )
        if not _strings(project.get("technologies")):
            gaps.append(
                Gap(
                    topic=Topic.TECHNOLOGIES,
                    item_id=item_id,
                    subject=name,
                    missing="no tools or languages are recorded for this project",
                )
            )

    if not skills:
        gaps.append(
            Gap(
                topic=Topic.SKILLS,
                item_id=None,
                subject="their skills",
                missing="no skills are recorded",
            )
        )
    if not certifications and education:
        gaps.append(
            Gap(
                topic=Topic.CERTIFICATIONS,
                item_id=None,
                subject="certifications",
                missing="no certification or licence is recorded",
            )
        )

    # Sharpening comes last, so a record is complete before anyone is asked to quantify it, and
    # stops after a few: the rest keep until the next conversation.
    if sum(1 for key in asked if key.startswith("impact_")) < MAX_IMPACT_QUESTIONS_PER_CONVERSATION:
        for index, role in enumerate(experience):
            gaps.extend(_impact_gaps(role, _identifier(role, index), _role_label(role), "work"))
        for index, project in enumerate(projects):
            gaps.extend(
                _impact_gaps(
                    project,
                    _identifier(project, index),
                    _text(project.get("name")) or "their project",
                    "project",
                )
            )

    already = set(asked)
    return sorted(
        (gap for gap in gaps if gap.key not in already),
        key=lambda gap: gap.topic,
    )


def next_gap(profile: Any, asked: Sequence[str] = ()) -> Gap | None:
    """The single most valuable thing left to ask about, or None when the record is enough."""
    gaps = open_gaps(profile, asked)
    return gaps[0] if gaps else None


def _role_label(role: dict[str, Any]) -> str:
    title = _text(role.get("title"))
    employer = _text(role.get("employer"))
    if title and employer:
        return f"{title} at {employer}"
    return title or employer or "their role"


def _quote(text: str) -> str:
    trimmed = text if len(text) <= 120 else f"{text[:117]}..."
    return f'"{trimmed}"'


def _identifier(item: dict[str, Any], index: int) -> str:
    raw = item.get("id")
    return raw.strip() if isinstance(raw, str) and raw.strip() else f"index-{index}"


def _items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, dict)]


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [text for entry in value if (text := _text(entry))]


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
