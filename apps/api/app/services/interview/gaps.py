"""What the record is still missing (PRD §23.1, §24).

Choosing the subject of the next question is a decision about the user's data, so code makes it,
not the model. The model is given one gap and asked to phrase a question about it. That keeps the
interview predictable, keeps it testable without a model, and stops it drifting into small talk.

The order of `Topic` is the priority order in PRD §24: experience before projects, what you did
before what you used, outcomes before education. A gap for an item the user has already been
asked about is skipped, so the interview moves on instead of nagging.
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

    EXPERIENCE = 1  # no roles recorded at all
    EXPERIENCE_DETAIL = 2  # a role with nothing said about it
    EXPERIENCE_OUTCOME = 3  # a role described only as duties, with no result
    TECHNOLOGIES = 4  # a role or project with no tools named
    PROJECTS = 5  # nothing built outside a job
    PROJECT_DETAIL = 6
    PROJECT_OUTCOME = 7
    SKILLS = 8
    EDUCATION = 9
    CERTIFICATIONS = 10


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


def open_gaps(profile: Any, asked: Sequence[str] = ()) -> list[Gap]:
    """Every gap in this profile, most valuable first, excluding ones already asked about."""
    experience = _items(getattr(profile, "experience", None))
    projects = _items(getattr(profile, "projects", None))
    skills = _items(getattr(profile, "skills", None))
    education = _items(getattr(profile, "education", None))
    certifications = _items(getattr(profile, "certifications", None))

    gaps: list[Gap] = []

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
    if not education:
        gaps.append(
            Gap(
                topic=Topic.EDUCATION,
                item_id=None,
                subject="their education",
                missing="no school, degree or course is recorded",
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
