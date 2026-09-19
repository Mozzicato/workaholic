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

from collections.abc import Sequence

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.models.candidate import (
    CandidateProfile,
    Evidence,
    Resume,
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
from app.services.resume.persistence import save_version
from app.services.resume.readiness import (
    DocumentKind,
    Readiness,
    ReadinessItem,
    assess_readiness,
)
from app.services.resume.record import (
    SourceBullet,
    collect_sources,
    item_id_of,
    items,
    items_awaiting_confirmation,
    profile_names,
    skill_names,
    strings,
    text_of,
)
from app.services.resume.validation import UnsupportedClaim, check_text, find_instruction

logger = structlog.get_logger(__name__)


class ProfileIncompleteError(AppError):
    def __init__(self, message: str, missing: Sequence[ReadinessItem] = ()) -> None:
        super().__init__(
            ErrorCode.PROFILE_INCOMPLETE,
            message,
            422,
            details=[{"field": item.key, "issue": item.hint} for item in missing],
        )

    @classmethod
    def from_readiness(cls, readiness: Readiness, document: str) -> "ProfileIncompleteError":
        labels = ", ".join(item.label.lower() for item in readiness.missing)
        return cls(
            f"Your record isn't ready for a {document} yet. Still needed: {labels}.",
            readiness.missing,
        )


class InstructionLikeContentError(AppError):
    """A profile line addresses the writer instead of describing what happened (PRD section 38).

    These lines are refused rather than sent. Text that says "make this sound senior" would
    otherwise license its own vocabulary in the checks that follow: the words it smuggles in
    would appear in the source it is checked against.
    """

    def __init__(self, offenders: Sequence[tuple[str, str]]) -> None:
        super().__init__(
            ErrorCode.PROFILE_CONTAINS_INSTRUCTIONS,
            "Some lines in your record tell the writer what to say instead of saying what you "
            "did. Rewrite them as plain statements of what happened, then try again.",
            422,
            details=[{"field": phrase, "issue": line} for phrase, line in offenders[:10]],
        )


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


class ResumeGenerationService:
    def __init__(self, session: AsyncSession, llm: LLMProvider) -> None:
        self._session = session
        self._llm = llm

    async def generate(
        self,
        *,
        user: User,
        resume: Resume,
        profile: CandidateProfile,
        evidence: Sequence[Evidence],
        template: ResumeTemplate = ResumeTemplate.STANDARD,
    ) -> ResumeVersion:
        readiness = assess_readiness(profile, DocumentKind.RESUME)
        if not readiness.ready:
            raise ProfileIncompleteError.from_readiness(readiness, "resume")

        blocked_items = items_awaiting_confirmation(evidence)
        sources = collect_sources(profile, blocked_items)

        offenders = [
            (phrase, source.text[:200])
            for source in sources
            if (phrase := find_instruction(source.text))
        ]
        if offenders:
            raise InstructionLikeContentError(offenders)

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
        self, resume: Resume, profile: CandidateProfile, sources: Sequence[SourceBullet]
    ) -> tuple[ResumeWording, str]:
        """One attempt, then one corrective retry naming exactly what was invented."""
        context = GenerationContext(
            target_role=resume.target_role,
            headline=text_of(profile.basics.get("headline")),
            summary=text_of(profile.basics.get("summary")),
            bullets=[
                BulletInput(id=source.id, text=source.text, context=source.context)
                for source in sources
            ],
            skills=skill_names(profile),
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
        return await save_version(
            self._session,
            user=user,
            resume=resume,
            content=document.model_dump(mode="json"),
            schema_version=SCHEMA_VERSION,
            prompt_version=GENERATE_PROMPT_VERSION,
            model=model,
            template=template,
        )


def _check_wording(
    wording: ResumeWording, sources: Sequence[SourceBullet], profile: CandidateProfile
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
                allowed_names=profile_names(profile),
            )
        )
    return problems


def _assemble(
    *,
    profile: CandidateProfile,
    sources: Sequence[SourceBullet],
    wording: ResumeWording,
    blocked_items: frozenset[str],
) -> ResumeDocument:
    """Build the document: facts straight from the record, wording from the checked rewrites."""
    rewritten = {bullet.id: bullet.text.strip() for bullet in wording.bullets}

    experience: list[ResumeExperience] = []
    for index, item in enumerate(items(profile.experience)):
        item_id = item_id_of(item, index)
        if item_id in blocked_items:
            continue
        employer, title = text_of(item.get("employer")), text_of(item.get("title"))
        if not (employer or title):
            continue
        bullets = _bullets_for(sources, rewritten, kind="experience", item_index=index)
        experience.append(
            ResumeExperience(
                item_id=item_id,
                employer=employer,
                title=title,
                location=text_of(item.get("location")),
                is_current=bool(item.get("is_current", False)),
                start_date=text_of(item.get("start_date")),
                end_date=None if item.get("is_current") else text_of(item.get("end_date")),
                bullets=bullets,
                technologies=strings(item.get("technologies")),
            )
        )

    projects: list[ResumeProject] = []
    for index, item in enumerate(items(profile.projects)):
        item_id = item_id_of(item, index)
        if item_id in blocked_items:
            continue
        projects.append(
            ResumeProject(
                item_id=item_id,
                name=text_of(item.get("name")) or "",
                url=text_of(item.get("url")),
                start_date=text_of(item.get("start_date")),
                end_date=text_of(item.get("end_date")),
                bullets=_bullets_for(sources, rewritten, kind="project", item_index=index),
                technologies=strings(item.get("technologies")),
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
    sources: Sequence[SourceBullet],
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


def _basics(profile: CandidateProfile) -> ResumeBasics:
    basics = profile.basics if isinstance(profile.basics, dict) else {}
    links = profile.links if isinstance(profile.links, dict) else {}
    named_links = [
        ResumeLink(label=label.title(), url=url)
        for label in ("website", "github", "linkedin")
        if (url := text_of(links.get(label)))
    ]
    for entry in items(links.get("other")):
        label, url = text_of(entry.get("label")), text_of(entry.get("url"))
        if label and url:
            named_links.append(ResumeLink(label=label, url=url))
    return ResumeBasics(
        full_name=text_of(basics.get("full_name")) or "",
        headline=text_of(basics.get("headline")),
        email=text_of(basics.get("email")),
        phone=text_of(basics.get("phone")),
        location=text_of(basics.get("location")),
        links=named_links[:10],
    )


def _education(profile: CandidateProfile, blocked_items: frozenset[str]) -> list[ResumeEducation]:
    entries: list[ResumeEducation] = []
    for index, item in enumerate(items(profile.education)):
        item_id = item_id_of(item, index)
        institution = text_of(item.get("institution"))
        if not institution or item_id in blocked_items:
            continue
        entries.append(
            ResumeEducation(
                item_id=item_id,
                institution=institution,
                qualification=text_of(item.get("qualification")),
                field_of_study=text_of(item.get("field_of_study")),
                grade=text_of(item.get("grade")),
                location=text_of(item.get("location")),
                start_date=text_of(item.get("start_date")),
                end_date=text_of(item.get("end_date")),
                details=strings(item.get("details"))[:10],
            )
        )
    return entries


def _certifications(
    profile: CandidateProfile, blocked_items: frozenset[str]
) -> list[ResumeCertification]:
    entries: list[ResumeCertification] = []
    for index, item in enumerate(items(profile.certifications)):
        item_id = item_id_of(item, index)
        name = text_of(item.get("name"))
        if not name or item_id in blocked_items:
            continue
        entries.append(
            ResumeCertification(
                item_id=item_id,
                name=name,
                issuer=text_of(item.get("issuer")),
                # Issued on `start_date`; `issued_date` only on rows written before that was fixed.
                issued_date=text_of(item.get("start_date")) or text_of(item.get("issued_date")),
            )
        )
    return entries


def _skill_groups(profile: CandidateProfile) -> list[ResumeSkillGroup]:
    grouped: dict[str, list[str]] = {}
    for item in items(profile.skills):
        name = text_of(item.get("name"))
        if not name:
            continue
        grouped.setdefault(text_of(item.get("category")) or "", []).append(name)
    return [
        ResumeSkillGroup(category=category or None, skills=names[:60])
        for category, names in list(grouped.items())[:12]
    ]


def _all_profile_text(profile: CandidateProfile, sources: Sequence[SourceBullet]) -> list[str]:
    """Everything the summary may draw on: the user's sentences and their own summary."""
    basics = profile.basics if isinstance(profile.basics, dict) else {}
    texts = [source.text for source in sources]
    texts.extend(filter(None, (text_of(basics.get("summary")), text_of(basics.get("headline")))))
    texts.extend(source.context for source in sources)
    texts.extend(skill_names(profile))
    return texts
