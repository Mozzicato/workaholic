"""Writing a cover letter from the career record.

The shape is the same as resume generation (ADR-005): the record supplies the facts, the model
supplies the arrangement, and deterministic checks decide whether what came back may be kept.

One difference matters. A cover letter is written against a job advert, and the advert is the
employer's text. It is given to the model as context so the letter leads with relevant
experience, but it is never part of the material a claim can be checked against — otherwise a
letter would simply repeat the requirements back as though the candidate had met them.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import CandidateProfile, Evidence, Resume, ResumeTemplate
from app.models.user import User
from app.prompts.cover_letter import (
    LetterContext,
    build_retry_message,
    build_write_messages,
)
from app.schemas.cover_letter import (
    CoverLetterDocument,
    LetterParagraph,
    LetterRecipient,
    LetterSender,
)
from app.services.ai.base import ChatMessage, LLMProvider
from app.services.resume.generation import (
    GenerationBlockedError,
    InstructionLikeContentError,
    ProfileIncompleteError,
)
from app.services.resume.record import (
    collect_sources,
    items,
    items_awaiting_confirmation,
    profile_names,
    skill_names,
    text_of,
)
from app.services.resume.validation import UnsupportedClaim, check_text, find_instruction

logger = structlog.get_logger(__name__)

MAX_ADVERT_LENGTH = 6000


@dataclass(frozen=True, slots=True)
class LetterBrief:
    """What the candidate is applying for. Their words, so their responsibility."""

    company: str
    role: str | None = None
    hiring_manager: str | None = None
    job_advert: str | None = None


class WrittenLetter(BaseModel):
    """What the model returns: three paragraphs, nothing else."""

    model_config = ConfigDict(extra="forbid")

    paragraphs: list[str]


class CoverLetterService:
    def __init__(self, session: AsyncSession, llm: LLMProvider) -> None:
        self._session = session
        self._llm = llm

    async def write(
        self,
        *,
        user: User,
        resume: Resume,
        profile: CandidateProfile,
        evidence: Sequence[Evidence],
        brief: LetterBrief,
        template: ResumeTemplate = ResumeTemplate.STANDARD,
    ) -> tuple[CoverLetterDocument, str]:
        """The letter, and the model that wrote it. Nothing is saved here."""
        blocked = items_awaiting_confirmation(evidence)
        sources = collect_sources(profile, blocked)
        if not sources:
            raise ProfileIncompleteError(
                "Add a role or project with at least one line about what you did, then we can "
                "write this letter from it."
            )

        offenders = [
            (phrase, source.text[:200])
            for source in sources
            if (phrase := find_instruction(source.text))
        ]
        if offenders:
            raise InstructionLikeContentError(offenders)

        material = [source.text for source in sources]
        basics = profile.basics if isinstance(profile.basics, dict) else {}
        context = LetterContext(
            company=brief.company,
            role=brief.role or resume.target_role,
            headline=text_of(basics.get("headline")),
            summary=text_of(basics.get("summary")),
            highlights=material,
            skills=skill_names(profile),
            job_advert=(brief.job_advert or "")[:MAX_ADVERT_LENGTH] or None,
        )

        paragraphs, model = await self._ask(context, profile, brief, material)
        return (
            _assemble(profile=profile, brief=brief, paragraphs=paragraphs, context=context),
            model,
        )

    async def _ask(
        self,
        context: LetterContext,
        profile: CandidateProfile,
        brief: LetterBrief,
        material: Sequence[str],
    ) -> tuple[list[str], str]:
        conversation: list[ChatMessage] = build_write_messages(context)
        allowed = _allowed_names(profile, brief)

        problems: list[UnsupportedClaim] = []
        for attempt in (1, 2):
            result = await self._llm.structured_output(
                conversation, WrittenLetter, operation="cover_letter.write"
            )
            paragraphs = [text.strip() for text in result.value.paragraphs if text.strip()]
            problems = _check(paragraphs, material, allowed)
            if paragraphs and not problems:
                return paragraphs, result.model

            logger.info(
                "cover_letter.unsupported_claims",
                attempt=attempt,
                problem_count=len(problems),
                kinds=sorted({problem.kind for problem in problems}),
            )
            if attempt == 1:
                conversation = [
                    *conversation,
                    ChatMessage(role="assistant", content="\n\n".join(paragraphs)),
                    build_retry_message([problem.for_prompt() for problem in problems]),
                ]

        raise GenerationBlockedError(problems)


def _check(
    paragraphs: Sequence[str], material: Sequence[str], allowed: Sequence[str]
) -> list[UnsupportedClaim]:
    problems: list[UnsupportedClaim] = []
    for index, paragraph in enumerate(paragraphs, start=1):
        problems.extend(
            check_text(
                location=f"paragraph {index}",
                rewritten=paragraph,
                sources=list(material),
                allowed_names=allowed,
            )
        )
    return problems


def _allowed_names(profile: CandidateProfile, brief: LetterBrief) -> list[str]:
    """Names a letter may use: everything in the record, plus what the candidate told us.

    The advert is not here. A letter may be shaped by it, but never claim anything because of it.
    """
    names = list(profile_names(profile))
    for value in (brief.company, brief.role, brief.hiring_manager):
        if value:
            names.extend(value.split())
    return names


def _assemble(
    *,
    profile: CandidateProfile,
    brief: LetterBrief,
    paragraphs: Sequence[str],
    context: LetterContext,
) -> CoverLetterDocument:
    basics = profile.basics if isinstance(profile.basics, dict) else {}
    person = text_of(brief.hiring_manager)
    return CoverLetterDocument(
        sender=LetterSender(
            full_name=text_of(basics.get("full_name")) or "",
            email=text_of(basics.get("email")),
            phone=text_of(basics.get("phone")),
            location=text_of(basics.get("location")),
        ),
        recipient=LetterRecipient(company=brief.company, person=person, role=context.role),
        written_on=datetime.now(UTC).date().isoformat(),
        salutation=f"Dear {person}," if person else "Dear hiring team,",
        paragraphs=[
            LetterParagraph(text=text, source_item_ids=_cited(text, profile)) for text in paragraphs
        ],
        closing="Yours sincerely,",
    )


def _cited(paragraph: str, profile: CandidateProfile) -> list[str]:
    """Which profile items this paragraph drew on, matched by the sentences it reuses."""
    cited: list[str] = []
    lowered = paragraph.lower()
    for key in ("experience", "projects"):
        for index, item in enumerate(items(getattr(profile, key, None))):
            texts = [
                value
                for field in ("bullets", "outcomes", "description")
                for value in _as_list(item.get(field))
            ]
            if any(_overlaps(text, lowered) for text in texts):
                identifier = item.get("id")
                cited.append(identifier if isinstance(identifier, str) else f"{key}-{index}")
    return cited[:20]


def _as_list(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, str)]
    return []


def _overlaps(source: str, paragraph: str) -> bool:
    """A rough citation: several distinctive words of a sentence appearing in the paragraph."""
    words = [word for word in source.lower().split() if len(word) > 4]
    if not words:
        return False
    matched = sum(1 for word in words if word in paragraph)
    return matched >= max(2, len(words) // 3)


CoverLetterBrief = LetterBrief
