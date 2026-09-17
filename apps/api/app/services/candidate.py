"""Candidate profile, evidence and resume behaviour.

Rules enforced here rather than in routes:
  - a user has exactly one profile, created on first use;
  - a section update replaces that section and nothing else;
  - evidence created through the API is `USER_PROVIDED`; anything a model proposes is
    `MODEL_INFERRED` and stays non-factual until the user confirms it (PRD §15).
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode, NotFoundError
from app.models.candidate import (
    CandidateProfile,
    Evidence,
    EvidenceSource,
    EvidenceStatus,
    ProfileSection,
    Resume,
    ResumeVersion,
)
from app.models.user import User
from app.repositories.candidate import (
    CandidateProfileRepository,
    EvidenceRepository,
    ResumeRepository,
    ResumeVersionRepository,
)
from app.schemas.candidate import (
    CandidateProfileUpdate,
    EvidenceCreate,
    ResumeCreate,
    ResumeUpdate,
)


class DuplicateResumeTitleError(AppError):
    def __init__(self) -> None:
        super().__init__(ErrorCode.CONFLICT, "You already have a resume with that name.", 409)


class CandidateProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._profiles = CandidateProfileRepository(session)

    async def get_or_create(self, user: User) -> CandidateProfile:
        profile = await self._profiles.get_for_user(user.id)
        if profile is not None:
            return profile
        profile = CandidateProfile(user_id=user.id)
        self._profiles.add(profile)
        try:
            await self._session.commit()
        except IntegrityError:
            # A concurrent first request created it; use that one.
            await self._session.rollback()
            existing = await self._profiles.get_for_user(user.id)
            if existing is None:  # pragma: no cover - the row exists by definition
                raise
            return existing
        await self._session.refresh(profile)
        return profile

    async def update_sections(self, user: User, update: CandidateProfileUpdate) -> CandidateProfile:
        profile = await self.get_or_create(user)
        for section, value in update.sections().items():
            setattr(profile, section, value)
        await self._session.commit()
        await self._session.refresh(profile)
        return profile


class EvidenceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._evidence = EvidenceRepository(session)
        self._profiles = CandidateProfileService(session)

    async def list_for_user(
        self, user: User, *, status: EvidenceStatus | None = None
    ) -> list[Evidence]:
        return await self._evidence.list_for_user(user.id, status=status)

    async def record(self, user: User, payload: EvidenceCreate) -> Evidence:
        """Record something the user stated. Their own statements are factual at once."""
        profile = await self._profiles.get_or_create(user)
        evidence = Evidence(
            user_id=user.id,
            candidate_profile_id=profile.id,
            claim=payload.claim,
            source=payload.source,
            source_reference=payload.source_reference,
            section=payload.section,
            item_id=payload.item_id,
            status=EvidenceStatus.USER_PROVIDED,
            confirmed_at=datetime.now(UTC),
        )
        self._evidence.add(evidence)
        await self._session.commit()
        await self._session.refresh(evidence)
        return evidence

    async def record_model_inference(
        self,
        user: User,
        claim: str,
        *,
        section: ProfileSection | None = None,
        item_id: str | None = None,
        source_reference: str | None = None,
    ) -> Evidence:
        """Record what a model proposed. Not factual until the user confirms it.

        `section` and `item_id` tie the proposal to the profile item it concerns, which is what
        lets resume generation leave that item out until the user confirms it.
        """
        profile = await self._profiles.get_or_create(user)
        evidence = Evidence(
            user_id=user.id,
            candidate_profile_id=profile.id,
            claim=claim,
            source=EvidenceSource.MODEL_SUGGESTION,
            source_reference=source_reference,
            section=section,
            item_id=item_id,
            status=EvidenceStatus.MODEL_INFERRED,
        )
        self._evidence.add(evidence)
        await self._session.commit()
        await self._session.refresh(evidence)
        return evidence

    async def confirm(self, user: User, evidence_id: uuid.UUID) -> Evidence:
        evidence = await self._require_owned(user, evidence_id)
        if not evidence.status.is_factual:
            evidence.status = EvidenceStatus.USER_CONFIRMED
            evidence.confirmed_at = datetime.now(UTC)
            await self._session.commit()
            await self._session.refresh(evidence)
        return evidence

    async def delete(self, user: User, evidence_id: uuid.UUID) -> None:
        evidence = await self._require_owned(user, evidence_id)
        await self._evidence.delete(evidence)
        await self._session.commit()

    async def _require_owned(self, user: User, evidence_id: uuid.UUID) -> Evidence:
        evidence = await self._evidence.get_owned(evidence_id, user.id)
        if evidence is None:
            raise NotFoundError("We couldn't find that evidence.")
        return evidence


class ResumeService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._resumes = ResumeRepository(session)
        self._versions = ResumeVersionRepository(session)
        self._profiles = CandidateProfileService(session)

    async def list_for_user(self, user: User) -> list[Resume]:
        return await self._resumes.list_for_user(user.id)

    async def create(self, user: User, payload: ResumeCreate) -> Resume:
        profile = await self._profiles.get_or_create(user)
        resume = Resume(
            user_id=user.id,
            candidate_profile_id=profile.id,
            title=payload.title,
            target_role=payload.target_role,
            document_type=payload.document_type,
        )
        self._resumes.add(resume)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateResumeTitleError() from exc
        await self._session.refresh(resume)
        return resume

    async def get(self, user: User, resume_id: uuid.UUID) -> Resume:
        resume = await self._resumes.get_owned(resume_id, user.id)
        if resume is None:
            raise NotFoundError("We couldn't find that resume.")
        return resume

    async def update(self, user: User, resume_id: uuid.UUID, payload: ResumeUpdate) -> Resume:
        resume = await self.get(user, resume_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(resume, field, value)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateResumeTitleError() from exc
        await self._session.refresh(resume)
        return resume

    async def delete(self, user: User, resume_id: uuid.UUID) -> None:
        resume = await self.get(user, resume_id)
        await self._resumes.delete(resume)
        await self._session.commit()

    async def list_versions(self, user: User, resume_id: uuid.UUID) -> list[ResumeVersion]:
        # Through the resume, so an unknown id is a 404 before any version is read.
        resume = await self.get(user, resume_id)
        return await self._versions.list_for_resume(resume.id, user.id)

    async def get_version(
        self, user: User, resume_id: uuid.UUID, version_id: uuid.UUID
    ) -> ResumeVersion:
        resume = await self.get(user, resume_id)
        version = await self._versions.get_owned(version_id, user.id)
        if version is None or version.resume_id != resume.id:
            raise NotFoundError("We couldn't find that version.")
        return version
