"""Turning a career record into a resume document (PRD §19, §36).

The pipeline is deliberate about who owns what:

    candidate profile ──> facts ────────────────────────────┐
            │                                               ├──> Resume JSON ──> version
            └──> the user's own sentences ──> model ──> wording (checked)

Employers, titles, dates, schools, certifications and skills never reach the model; they are
copied from the record into the document. The model receives only sentences the user wrote and
returns rewritten sentences, each of which is checked against its source before it is kept. If
the check fails twice, generation is blocked and the user is told what was added — a resume is
never quietly published with a claim they did not make.
"""

import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.models.candidate import (
    CandidateProfile,
    Evidence,
    Resume,
    ResumeStatus,
    ResumeTemplate,
    ResumeVersion,
)
from app.models.user import User
from app.prompts.resume import (
    GENERATE_PROMPT_VERSION,
    build_generate_messages,
    build_retry_message,
)
from app.prompts.resume.generate import BulletInput, GenerationContext
from app.repositories.candidate import ResumeVersionRepository
from app.schemas.resume_document import (
    SCHEMA_VERSION,
    Bullet,
    ResumeBasics,
    ResumeCertification,
    ResumeDocument,
    ResumeEducation,
    ResumeExperience,
    ResumeLink,
    ResumeProject,
    ResumeSkillGroup,
)
from app.services.ai.base import ChatMessage, LLMProvider
from app.services.resume.validation import UnsupportedClaim, check_text

logger = structlog.get_logger(__name__)

MAX_BULLETS = 60
"""A ceiling on how much wording one request may rewrite, so cost per call stays predictable."""


class ProfileIncompleteError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(ErrorCode.PROFILE_INCOMPLETE, message, 422)


class GenerationBlockedError(AppError):
    """The wording could not be trusted, twice. Nothing was saved."""

    def __init__(self, problems: Sequence[UnsupportedClaim]) -> None:
        super().__init__(
            ErrorCode.GENERATION_BLOCKED,
            "We stopped this draft because the wording went beyond what you told us. "
            "Nothing was saved. Add the missing detail to your record, then try again.",
            422,
            details=[
                {"field": problem.location, "issue": problem.message} for problem in problems[:10]
            ],
        )


class RewrittenBullet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    text: str


class ResumeWording(BaseModel):
    """What the model returns: wording only, never facts."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(description="Two or three sentences, or empty if unsupported")
    bullets: list[RewrittenBullet]


@dataclass(frozen=True, slots=True)
class _SourceBullet:
    """A sentence from the record, and where it belongs in the document."""

    id: str
    kind: str  # "experience" | "project"
    item_id: str
    item_index: int
    bullet_index: int
    text: str
    context: str
    allowed_names: tuple[str, ...]


class ResumeGenerationService:
    def __init__(self, session: AsyncSession, llm: LLMProvider) -> None:
        self._session = session
        self._llm = llm
        self._versions = ResumeVersionRepository(session)

    async def generate(
        self,
        *,
        user: User,
        resume: Resume,
        profile: CandidateProfile,
        evidence: Sequence[Evidence],
        template: ResumeTemplate = ResumeTemplate.STANDARD,
    ) -> ResumeVersion:
        blocked_items = _items_awaiting_confirmation(evidence)
        sources = _collect_sources(profile, blocked_items)
        if not sources:
            raise ProfileIncompleteError(
                "Add a role or project with at least one line about what you did, then we can "
                "write this resume from it."
            )

        wording, model_name = await self._ask_for_wording(resume, profile, sources)
        document = _assemble(
            profile=profile,
            sources=sources,
            wording=wording,
            blocked_items=blocked_items,
        )
        return await self._save(
            user=user, resume=resume, document=document, template=template, model=model_name
        )

    async def _ask_for_wording(
        self, resume: Resume, profile: CandidateProfile, sources: Sequence[_SourceBullet]
    ) -> tuple[ResumeWording, str]:
        """One attempt, then one corrective retry naming exactly what was invented."""
        context = GenerationContext(
            target_role=resume.target_role,
            headline=_text(profile.basics.get("headline")),
            summary=_text(profile.basics.get("summary")),
            bullets=[
                BulletInput(id=source.id, text=source.text, context=source.context)
                for source in sources
            ],
            skills=_skill_names(profile),
        )
        conversation: list[ChatMessage] = build_generate_messages(context)

        problems: list[UnsupportedClaim] = []
        for attempt in (1, 2):
            result = await self._llm.structured_output(
                conversation, ResumeWording, operation="resume.generate"
            )
            wording = result.value
            problems = _check_wording(wording, sources, profile)
            if not problems:
                return wording, result.model

            logger.info(
                "resume.generate.unsupported_claims",
                attempt=attempt,
                # Counts and kinds only: claim text is resume content and is never logged.
                problem_count=len(problems),
                kinds=sorted({problem.kind for problem in problems}),
            )
            if attempt == 1:
                conversation = [
                    *conversation,
                    ChatMessage(role="assistant", content=wording.model_dump_json()),
                    build_retry_message([problem.for_prompt() for problem in problems]),
                ]

        raise GenerationBlockedError(problems)

    async def _save(
        self,
        *,
        user: User,
        resume: Resume,
        document: ResumeDocument,
        template: ResumeTemplate,
        model: str,
    ) -> ResumeVersion:
        next_number = await self._versions.next_version_number(resume.id)
        version = ResumeVersion(
            user_id=user.id,
            resume_id=resume.id,
            version_number=next_number,
            label=f"Version {next_number}",
            content=document.model_dump(mode="json"),
            template=template,
            schema_version=SCHEMA_VERSION,
            prompt_version=GENERATE_PROMPT_VERSION,
            model=model,
        )
        self._versions.add(version)
        await self._session.flush()
        resume.current_version_id = version.id
        resume.status = ResumeStatus.READY
        await self._session.commit()
        await self._session.refresh(version)
        return version


def _check_wording(
    wording: ResumeWording, sources: Sequence[_SourceBullet], profile: CandidateProfile
) -> list[UnsupportedClaim]:
    by_id = {source.id: source for source in sources}
    returned = {bullet.id: bullet.text for bullet in wording.bullets}

    problems: list[UnsupportedClaim] = [
        UnsupportedClaim(
            location=bullet_id,
            kind="name",
            token=bullet_id,
            message="this line does not match anything in your record",
        )
        for bullet_id in returned
        if bullet_id not in by_id
    ]

    for source in sources:
        text = returned.get(source.id)
        if text is None:
            continue  # a dropped line loses nothing that was not already the user's
        problems.extend(
            check_text(
                location=source.id,
                rewritten=text,
                sources=[source.text],
                allowed_names=source.allowed_names,
            )
        )

    if wording.summary.strip():
        problems.extend(
            check_text(
                location="summary",
                rewritten=wording.summary,
                sources=_all_profile_text(profile, sources),
                allowed_names=_all_profile_names(profile),
            )
        )
    return problems


def _assemble(
    *,
    profile: CandidateProfile,
    sources: Sequence[_SourceBullet],
    wording: ResumeWording,
    blocked_items: frozenset[str],
) -> ResumeDocument:
    """Build the document: facts straight from the record, wording from the checked rewrites."""
    rewritten = {bullet.id: bullet.text.strip() for bullet in wording.bullets}

    experience: list[ResumeExperience] = []
    for index, item in enumerate(_items(profile.experience)):
        item_id = _item_id(item, index)
        if item_id in blocked_items:
            continue
        bullets = _bullets_for(sources, rewritten, kind="experience", item_index=index)
        experience.append(
            ResumeExperience(
                item_id=item_id,
                employer=_text(item.get("employer")) or "",
                title=_text(item.get("title")) or "",
                location=_text(item.get("location")),
                is_current=bool(item.get("is_current", False)),
                start_date=_text(item.get("start_date")),
                end_date=None if item.get("is_current") else _text(item.get("end_date")),
                bullets=bullets,
                technologies=_strings(item.get("technologies")),
            )
        )

    projects: list[ResumeProject] = []
    for index, item in enumerate(_items(profile.projects)):
        item_id = _item_id(item, index)
        if item_id in blocked_items:
            continue
        projects.append(
            ResumeProject(
                item_id=item_id,
                name=_text(item.get("name")) or "",
                url=_text(item.get("url")),
                start_date=_text(item.get("start_date")),
                end_date=_text(item.get("end_date")),
                bullets=_bullets_for(sources, rewritten, kind="project", item_index=index),
                technologies=_strings(item.get("technologies")),
            )
        )

    return ResumeDocument(
        basics=_basics(profile),
        summary=wording.summary.strip() or None,
        experience=experience,
        education=_education(profile, blocked_items),
        projects=projects,
        skills=_skill_groups(profile),
        certifications=_certifications(profile, blocked_items),
    )


def _bullets_for(
    sources: Sequence[_SourceBullet],
    rewritten: dict[str, str],
    *,
    kind: str,
    item_index: int,
) -> list[Bullet]:
    bullets: list[Bullet] = []
    for source in sources:
        if source.kind != kind or source.item_index != item_index:
            continue
        # No rewrite came back for this line: keep the user's own words rather than lose it.
        text = rewritten.get(source.id) or source.text
        bullets.append(
            Bullet(
                text=text[:500],
                source_item_id=source.item_id,
                source_bullet_index=source.bullet_index,
            )
        )
    return bullets


def _collect_sources(
    profile: CandidateProfile, blocked_items: frozenset[str]
) -> list[_SourceBullet]:
    """Every sentence the user wrote, with the names its rewrite may legitimately use."""
    sources: list[_SourceBullet] = []
    profile_names = _all_profile_names(profile)

    for index, item in enumerate(_items(profile.experience)):
        item_id = _item_id(item, index)
        if item_id in blocked_items:
            continue
        employer = _text(item.get("employer")) or ""
        title = _text(item.get("title")) or ""
        context = " at ".join(part for part in (title, employer) if part) or "a role"
        allowed = (*profile_names, *_strings(item.get("technologies")), employer, title)
        for position, bullet in enumerate(_strings(item.get("bullets"))):
            sources.append(
                _SourceBullet(
                    id=f"e{index}.b{position}",
                    kind="experience",
                    item_id=item_id,
                    item_index=index,
                    bullet_index=position,
                    text=bullet,
                    context=context,
                    allowed_names=tuple(name for name in allowed if name),
                )
            )

    for index, item in enumerate(_items(profile.projects)):
        item_id = _item_id(item, index)
        if item_id in blocked_items:
            continue
        name = _text(item.get("name")) or "a project"
        allowed = (*profile_names, *_strings(item.get("technologies")), name)
        outcomes = _strings(item.get("outcomes"))
        description = _text(item.get("description"))
        texts = ([description] if description else []) + outcomes
        for position, bullet in enumerate(texts):
            sources.append(
                _SourceBullet(
                    id=f"p{index}.b{position}",
                    kind="project",
                    item_id=item_id,
                    item_index=index,
                    bullet_index=position,
                    text=bullet,
                    context=name,
                    allowed_names=tuple(entry for entry in allowed if entry),
                )
            )

    return sources[:MAX_BULLETS]


def _items_awaiting_confirmation(evidence: Sequence[Evidence]) -> frozenset[str]:
    """Profile items whose evidence a model proposed and the user has not confirmed (PRD §15)."""
    return frozenset(
        record.item_id for record in evidence if record.item_id and not record.status.is_factual
    )


def _basics(profile: CandidateProfile) -> ResumeBasics:
    basics = profile.basics if isinstance(profile.basics, dict) else {}
    links = profile.links if isinstance(profile.links, dict) else {}
    named_links = [
        ResumeLink(label=label.title(), url=url)
        for label in ("website", "github", "linkedin")
        if (url := _text(links.get(label)))
    ]
    for entry in _items(links.get("other")):
        label, url = _text(entry.get("label")), _text(entry.get("url"))
        if label and url:
            named_links.append(ResumeLink(label=label, url=url))
    return ResumeBasics(
        full_name=_text(basics.get("full_name")) or "",
        headline=_text(basics.get("headline")),
        email=_text(basics.get("email")),
        phone=_text(basics.get("phone")),
        location=_text(basics.get("location")),
        links=named_links[:10],
    )


def _education(profile: CandidateProfile, blocked_items: frozenset[str]) -> list[ResumeEducation]:
    entries: list[ResumeEducation] = []
    for index, item in enumerate(_items(profile.education)):
        item_id = _item_id(item, index)
        institution = _text(item.get("institution"))
        if not institution or item_id in blocked_items:
            continue
        entries.append(
            ResumeEducation(
                item_id=item_id,
                institution=institution,
                qualification=_text(item.get("qualification")),
                field_of_study=_text(item.get("field_of_study")),
                location=_text(item.get("location")),
                start_date=_text(item.get("start_date")),
                end_date=_text(item.get("end_date")),
                details=_strings(item.get("details"))[:10],
            )
        )
    return entries


def _certifications(
    profile: CandidateProfile, blocked_items: frozenset[str]
) -> list[ResumeCertification]:
    entries: list[ResumeCertification] = []
    for index, item in enumerate(_items(profile.certifications)):
        item_id = _item_id(item, index)
        name = _text(item.get("name"))
        if not name or item_id in blocked_items:
            continue
        entries.append(
            ResumeCertification(
                item_id=item_id,
                name=name,
                issuer=_text(item.get("issuer")),
                issued_date=_text(item.get("issued_date")),
            )
        )
    return entries


def _skill_groups(profile: CandidateProfile) -> list[ResumeSkillGroup]:
    grouped: dict[str, list[str]] = {}
    for item in _items(profile.skills):
        name = _text(item.get("name"))
        if not name:
            continue
        grouped.setdefault(_text(item.get("category")) or "", []).append(name)
    return [
        ResumeSkillGroup(category=category or None, skills=names[:60])
        for category, names in list(grouped.items())[:12]
    ]


def _skill_names(profile: CandidateProfile) -> list[str]:
    return [name for item in _items(profile.skills) if (name := _text(item.get("name")))]


def _all_profile_text(profile: CandidateProfile, sources: Sequence[_SourceBullet]) -> list[str]:
    """Everything the summary may draw on: the user's sentences and their own summary."""
    basics = profile.basics if isinstance(profile.basics, dict) else {}
    texts = [source.text for source in sources]
    texts.extend(filter(None, (_text(basics.get("summary")), _text(basics.get("headline")))))
    texts.extend(source.context for source in sources)
    texts.extend(_skill_names(profile))
    return texts


def _all_profile_names(profile: CandidateProfile) -> tuple[str, ...]:
    """Names the record holds: employers, titles, schools, tools, skills, the user's own name."""
    basics = profile.basics if isinstance(profile.basics, dict) else {}
    names: list[str] = [_text(basics.get("full_name")) or ""]
    for item in _items(profile.experience):
        names.extend([_text(item.get("employer")) or "", _text(item.get("title")) or ""])
        names.extend(_strings(item.get("technologies")))
    for item in _items(profile.projects):
        names.append(_text(item.get("name")) or "")
        names.extend(_strings(item.get("technologies")))
    for item in _items(profile.education):
        names.extend(
            [
                _text(item.get("institution")) or "",
                _text(item.get("qualification")) or "",
                _text(item.get("field_of_study")) or "",
            ]
        )
    for item in _items(profile.certifications):
        names.extend([_text(item.get("name")) or "", _text(item.get("issuer")) or ""])
    names.extend(_skill_names(profile))
    # Names are matched word by word, so multi-word names contribute each of their words.
    words = {word for name in names if name for word in name.split()}
    return tuple(sorted(words))


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


def _item_id(item: dict[str, Any], index: int) -> str:
    """Profile items carry a generated id; fall back to position for records written before that."""
    raw = item.get("id")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()[:36]
    return str(uuid.uuid5(uuid.NAMESPACE_OID, f"item-{index}"))
