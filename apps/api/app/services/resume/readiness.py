"""Is the record complete enough to write a document from?

A resume is not written until the record holds what a resume needs. It is the product's job to
notice that education is missing *before* writing — not the ATS checker's job to point it out
afterwards, on a document someone may already have sent.

Deliberately, experience and projects count together: someone who has not yet had a job must
still be able to build a resume from what they built, rather than being pushed to invent a role.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from app.services.resume.record import items, strings, text_of

__all__ = ["DocumentKind", "Readiness", "ReadinessItem", "assess_readiness"]


class DocumentKind(StrEnum):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"


@dataclass(frozen=True, slots=True)
class ReadinessItem:
    key: str
    label: str
    done: bool
    hint: str


@dataclass(frozen=True, slots=True)
class Readiness:
    items: list[ReadinessItem]

    @property
    def ready(self) -> bool:
        return all(item.done for item in self.items)

    @property
    def missing(self) -> list[ReadinessItem]:
        return [item for item in self.items if not item.done]


def assess_readiness(profile: Any, kind: DocumentKind = DocumentKind.RESUME) -> Readiness:
    """What the record holds, and what it still needs, for this kind of document."""
    basics = getattr(profile, "basics", None)
    basics = basics if isinstance(basics, dict) else {}

    name = bool(text_of(basics.get("full_name")))
    contact = bool(text_of(basics.get("email")) or text_of(basics.get("phone")))
    education = any(text_of(entry.get("institution")) for entry in items(profile.education))
    work = _has_described_work(profile)
    skills = any(text_of(entry.get("name")) for entry in items(profile.skills))

    checklist = [
        ReadinessItem(
            key="name",
            label="Your name",
            done=name,
            hint="The name at the top of the page.",
        ),
        ReadinessItem(
            key="contact",
            label="A way to contact you",
            done=contact,
            hint="An email address or phone number, so an employer can reply.",
        ),
        ReadinessItem(
            key="experience_or_projects",
            label="Something you've done",
            done=work,
            hint=(
                "A job, internship or project, with at least one line about what you did. "
                "A project counts — you don't need a job to have a resume."
            ),
        ),
    ]
    if kind is DocumentKind.RESUME:
        checklist.insert(
            2,
            ReadinessItem(
                key="education",
                label="Your education",
                done=education,
                hint="Where you studied, or are studying.",
            ),
        )
        checklist.append(
            ReadinessItem(
                key="skills",
                label="Your skills",
                done=skills,
                hint="The skills you'd be comfortable being asked about.",
            )
        )
    return Readiness(items=checklist)


def _has_described_work(profile: Any) -> bool:
    """A role or project with at least one sentence about it — a title alone is not enough."""
    for role in items(profile.experience):
        if strings(role.get("bullets")):
            return True
    for project in items(profile.projects):
        if text_of(project.get("description")) or strings(project.get("outcomes")):
            return True
    return False
