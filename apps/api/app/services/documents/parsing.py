"""Turning an uploaded resume into items the user can confirm (PRD §37).

Nothing here writes to the career record. An upload produces a *proposal*: items the document
appears to contain, each checked against the document's own text, which the user then accepts or
discards. That is the "user confirmation" step of the PRD's pipeline, and it is the reason an
upload cannot quietly put a stranger's claims — or a mis-parse — into someone's record.
"""

from dataclasses import dataclass

import structlog
from pydantic import BaseModel, ConfigDict

from app.prompts.documents import PARSE_PROMPT_VERSION, build_parse_messages
from app.prompts.documents.parse import ParseContext
from app.services.ai.base import LLMProvider
from app.services.interview.extraction import ExtractedFacts, grade_stated, ground
from app.services.resume.validation import check_text, vocabulary_of

logger = structlog.get_logger(__name__)

__all__ = ["ParsedDocument", "ParsedProject", "ParsedRole", "parse_document"]


class ParsedRole(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employer: str
    title: str
    start_date: str
    end_date: str
    bullets: list[str]
    technologies: list[str]


class ParsedProject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    technologies: list[str]


class ParsedEducation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    institution: str
    qualification: str
    field_of_study: str
    start_date: str
    end_date: str
    # Defaulted so a client from before grades were read can still accept an import.
    grade: str = ""


class DocumentContents(BaseModel):
    """What the model reports the document says. Checked before anything is offered."""

    model_config = ConfigDict(extra="forbid")

    full_name: str
    email: str
    phone: str
    location: str
    headline: str
    summary: str
    roles: list[ParsedRole]
    projects: list[ParsedProject]
    education: list[ParsedEducation]
    skills: list[str]


@dataclass(slots=True)
class ParsedDocument:
    """A proposal, not a record. `dropped` is what the document did not support."""

    contents: DocumentContents
    dropped: list[str]
    prompt_version: str = PARSE_PROMPT_VERSION
    model: str = ""

    @property
    def is_empty(self) -> bool:
        contents = self.contents
        return not (
            contents.roles
            or contents.projects
            or contents.education
            or contents.skills
            or contents.full_name
        )


async def parse_document(llm: LLMProvider, text: str) -> ParsedDocument:
    """Read the document, then keep only what the document itself supports."""
    result = await llm.structured_output(
        build_parse_messages(ParseContext(text=text)),
        DocumentContents,
        operation="documents.parse",
    )
    kept, dropped = _ground(result.value, text)
    logger.info(
        "documents.parsed",
        # Counts only: an uploaded resume is somebody's career, and never goes in a log.
        roles=len(kept.roles),
        projects=len(kept.projects),
        skills=len(kept.skills),
        dropped=len(dropped),
    )
    return ParsedDocument(contents=kept, dropped=dropped, model=result.model)


def _ground(contents: DocumentContents, text: str) -> tuple[DocumentContents, list[str]]:
    """Keep what the document says; drop what the model added to it."""
    dropped: list[str] = []
    vocabulary = vocabulary_of([text])

    def named(value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            return ""
        # The same tokeniser as every other check, so "Next.js", "C++" and "C#" are words.
        words = vocabulary_of([cleaned]) - _JOINING_WORDS
        if words and words <= vocabulary:
            return cleaned
        dropped.append(cleaned)
        return ""

    def sentence(value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            return ""
        if check_text(location="document", rewritten=cleaned, sources=[text]):
            dropped.append(cleaned)
            return ""
        return cleaned

    roles = []
    for role in contents.roles:
        grounded = ground(_as_facts(role), text)
        employer, title = named(role.employer), named(role.title)
        if not (employer or title):
            continue
        roles.append(
            ParsedRole(
                employer=employer,
                title=title,
                start_date=grounded.start_date,
                end_date=grounded.end_date,
                bullets=[
                    kept
                    for line in role.bullets
                    if not _is_label_line(line) and (kept := sentence(line))
                ],
                technologies=[kept for tool in role.technologies if (kept := named(tool))],
            )
        )
        dropped.extend(grounded.dropped)

    projects = [
        ParsedProject(
            name=name,
            description=sentence(project.description),
            technologies=[kept for tool in project.technologies if (kept := named(tool))],
        )
        for project in contents.projects
        if (name := named(project.name))
    ]

    education = [
        ParsedEducation(
            institution=institution,
            qualification=(qualification := named(entry.qualification)),
            field_of_study=_unless_repeated(named(entry.field_of_study), qualification),
            start_date=entry.start_date if entry.start_date[:4] in text else "",
            end_date=entry.end_date if entry.end_date[:4] in text else "",
            grade=entry.grade.strip() if grade_stated(entry.grade, text) else "",
        )
        for entry in contents.education
        if (institution := named(entry.institution))
    ]

    supported = DocumentContents(
        full_name=named(contents.full_name),
        email=contents.email if contents.email and contents.email in text else "",
        phone=contents.phone if contents.phone and _digits(contents.phone) in _digits(text) else "",
        location=named(contents.location),
        headline=sentence(contents.headline),
        summary=sentence(contents.summary),
        roles=roles,
        projects=projects,
        education=education,
        skills=[kept for skill in contents.skills if (kept := named(skill))],
    )
    return supported, dropped


def _as_facts(role: ParsedRole) -> ExtractedFacts:
    """Reuse the interview's date grounding, which already knows how to read a stated date."""
    return ExtractedFacts(
        usable=True,
        full_name="",
        email="",
        phone="",
        location="",
        employer=role.employer,
        title=role.title,
        start_date=role.start_date,
        end_date=role.end_date,
        is_current=False,
        project_name="",
        description="",
        bullets=[],
        outcomes=[],
        technologies=[],
        skills=[],
        institution="",
        qualification="",
        field_of_study="",
        grade="",
        certification_name="",
    )


_JOINING_WORDS = frozenset({"a", "an", "and", "at", "for", "in", "of", "on", "the", "to", "with"})

# Lines a CV uses as labels for a list, which the model tends to copy in as bullets.
_LABELS = ("technologies:", "tools:", "stack:", "tech stack:", "skills:", "languages:")


def _is_label_line(line: str) -> bool:
    return line.strip().lower().startswith(_LABELS)


def _unless_repeated(field: str, qualification: str) -> str:
    """Drop a field of study the qualification already names, so it is not printed twice."""
    return "" if field and field.lower() in qualification.lower() else field


def _digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())
